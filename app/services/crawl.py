import hashlib
import re
from typing import Any, Optional

from app.clients.crossref import CrossrefClient
from app.clients.openalex import OpenAlexClient
from app.clients.unpaywall import UnpaywallClient
from app.config import get_settings
from app.db import dict_from_row, get_conn
from app.utils import json_dumps, json_loads, now_iso, today_iso


def normalize_keyword_config(keyword_config: Any) -> tuple[str, list[str]]:
    if isinstance(keyword_config, dict):
        mode = str(keyword_config.get("mode") or "or").lower()
        terms = keyword_config.get("terms") or keyword_config.get("keywords") or []
    else:
        mode = "or"
        terms = keyword_config or []
    if isinstance(terms, str):
        terms = [terms]
    normalized_terms = [str(term).strip().lower() for term in terms if str(term).strip()]
    return ("and" if mode == "and" else "or", normalized_terms)


def matches_keywords(work: dict[str, Any], keywords: Any) -> bool:
    mode, terms = normalize_keyword_config(keywords)
    if not terms:
        return True
    haystack = f"{work.get('title') or ''}\n{work.get('abstract') or ''}".lower()
    if mode == "and":
        return all(term in haystack for term in terms)
    return any(term in haystack for term in terms)


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def normalize_doi(value: Any) -> Optional[str]:
    doi = normalize_text(value)
    if not doi:
        return None
    return doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/")


def build_dedupe_key(journal: dict[str, Any], work: dict[str, Any]) -> Optional[str]:
    doi = normalize_doi(work.get("doi"))
    if doi:
        return f"doi:{doi}"
    title = normalize_text(work.get("title"))
    if not title:
        return None
    date_hint = normalize_text(work.get("published_date") or work.get("published_year"))
    landing_url = normalize_text(work.get("landing_url"))
    if not date_hint and not landing_url:
        return None
    fingerprint = "|".join([str(journal["id"]), title, date_hint, landing_url])
    return f"no-doi:{hashlib.sha256(fingerprint.encode('utf-8')).hexdigest()}"


def upsert_paper(conn, journal: dict[str, Any], work: dict[str, Any], oa: dict[str, Any]) -> bool:
    doi = normalize_doi(work.get("doi"))
    dedupe_key = build_dedupe_key(journal, work)
    existing = None
    if doi:
        existing = conn.execute("SELECT id FROM papers WHERE doi = ?", (doi,)).fetchone()
    elif dedupe_key:
        existing = conn.execute("SELECT id FROM papers WHERE dedupe_key = ?", (dedupe_key,)).fetchone()
    payload = (
        doi,
        work.get("title") or "Untitled",
        work.get("abstract") or "",
        json_dumps(work.get("authors") or []),
        journal["id"],
        work.get("journal_name") or journal["name"],
        work.get("published_date"),
        work.get("published_year"),
        work.get("landing_url"),
        oa.get("oa_status") or "unknown",
        oa.get("oa_pdf_url"),
        work.get("source_api"),
        dedupe_key,
        json_dumps(work.get("raw_metadata") or {}),
        now_iso(),
    )
    if existing:
        conn.execute(
            """
            UPDATE papers
            SET title=?, abstract=?, authors=?, journal_id=?, journal_name=?, published_date=?,
                published_year=?, landing_url=?, oa_status=?, oa_pdf_url=?, source_api=?,
                dedupe_key=?, raw_metadata=?, updated_at=?
            WHERE id=?
            """,
            payload[1:] + (existing["id"],),
        )
        return False
    conn.execute(
        """
        INSERT INTO papers (
            doi, title, abstract, authors, journal_id, journal_name, published_date,
            published_year, landing_url, oa_status, oa_pdf_url, source_api, dedupe_key, raw_metadata,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )
    return True


def academic_client_options(settings) -> dict[str, Any]:
    return {
        "max_retries": settings.academic_api_max_retries,
        "retry_backoff_seconds": settings.academic_api_retry_backoff_seconds,
        "timeout": settings.academic_api_timeout_seconds,
    }


async def fetch_metadata_works(settings, issn: str, date_from: str, date_to: str) -> tuple[list[dict[str, Any]], Optional[str]]:
    client_options = academic_client_options(settings)
    openalex_error = None
    try:
        works = await OpenAlexClient(settings.openalex_mailto, **client_options).works_by_issn(
            issn, date_from, date_to, max_pages=settings.academic_api_max_pages
        )
        if works:
            return works, None
    except Exception as exc:
        openalex_error = str(exc)

    works = await CrossrefClient(settings.openalex_mailto, **client_options).works_by_issn(
        issn, date_from, date_to, max_pages=settings.academic_api_max_pages
    )
    if openalex_error:
        return works, f"OpenAlex failed; used Crossref fallback: {openalex_error}"
    return works, None


async def run_crawl_job(job_id: int, journal_id: int, date_from: str, date_to: str) -> None:
    settings = get_settings()
    with get_conn() as conn:
        conn.execute(
            "UPDATE crawl_jobs SET status='running', started_at=? WHERE id=?",
            (now_iso(), job_id),
        )
        journal_row = conn.execute("SELECT * FROM journals WHERE id=?", (journal_id,)).fetchone()
        if not journal_row:
            conn.execute(
                "UPDATE crawl_jobs SET status='failed', error=?, finished_at=? WHERE id=?",
                ("journal not found", now_iso(), job_id),
            )
            return
        journal = dict_from_row(journal_row)

    try:
        issn = journal.get("issn_electronic") or journal.get("issn_print")
        if not issn:
            raise RuntimeError("journal has no ISSN")
        works, source_warning = await fetch_metadata_works(settings, issn, date_from, date_to)

        keywords = json_loads(journal.get("keywords"), [])
        found = len(works)
        filtered = 0
        new_count = 0
        unpaywall = UnpaywallClient(settings.unpaywall_email)
        with get_conn() as conn:
            for work in works:
                if not matches_keywords(work, keywords):
                    filtered += 1
                    continue
                oa = {"oa_status": "unknown", "oa_pdf_url": None}
                if work.get("doi"):
                    try:
                        oa = await unpaywall.resolve(work["doi"])
                    except Exception as exc:
                        oa = {"oa_status": "unknown", "oa_pdf_url": None, "error": str(exc)}
                if upsert_paper(conn, journal, work, oa):
                    new_count += 1
            conn.execute(
                """
                UPDATE crawl_jobs
                SET status='success', papers_found=?, papers_filtered=?, papers_new=?, error=?, finished_at=?
                WHERE id=?
                """,
                (found, filtered, new_count, source_warning, now_iso(), job_id),
            )
    except Exception as exc:
        with get_conn() as conn:
            conn.execute(
                "UPDATE crawl_jobs SET status='failed', error=?, finished_at=? WHERE id=?",
                (str(exc), now_iso(), job_id),
            )


def create_jobs(journal_ids: Optional[list[int]], period: str, date_from: Optional[str], date_to: Optional[str]) -> list[dict[str, Any]]:
    date_to = date_to or today_iso()
    with get_conn() as conn:
        if journal_ids:
            placeholders = ",".join("?" for _ in journal_ids)
            journals = conn.execute(
                f"SELECT * FROM journals WHERE active=1 AND id IN ({placeholders})", tuple(journal_ids)
            ).fetchall()
        else:
            journals = conn.execute("SELECT * FROM journals WHERE active=1").fetchall()
        jobs = []
        for row in journals:
            journal = dict_from_row(row)
            start = date_from
            if not start:
                last = conn.execute(
                    """
                    SELECT date_to FROM crawl_jobs
                    WHERE journal_id=? AND status='success' AND date_to IS NOT NULL
                    ORDER BY finished_at DESC, id DESC LIMIT 1
                    """,
                    (journal["id"],),
                ).fetchone()
                start = last["date_to"] if last else f"{journal.get('year_from') or 1990}-01-01"
            cursor = conn.execute(
                """
                INSERT INTO crawl_jobs (journal_id, period, date_from, date_to, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (journal["id"], period, start, date_to),
            )
            jobs.append({"job_id": cursor.lastrowid, "journal_id": journal["id"], "date_from": start, "date_to": date_to})
        return jobs
