from typing import Any, Optional

from app.clients.crossref import CrossrefClient
from app.clients.openalex import OpenAlexClient
from app.clients.unpaywall import UnpaywallClient
from app.config import get_settings
from app.db import dict_from_row, get_conn
from app.utils import json_dumps, json_loads, now_iso, today_iso


def matches_keywords(work: dict[str, Any], keywords: list[str]) -> bool:
    if not keywords:
        return True
    haystack = f"{work.get('title') or ''}\n{work.get('abstract') or ''}".lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def upsert_paper(conn, journal: dict[str, Any], work: dict[str, Any], oa: dict[str, Any]) -> bool:
    doi = work.get("doi")
    existing = None
    if doi:
        existing = conn.execute("SELECT id FROM papers WHERE doi = ?", (doi,)).fetchone()
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
        json_dumps(work.get("raw_metadata") or {}),
        now_iso(),
    )
    if existing:
        conn.execute(
            """
            UPDATE papers
            SET title=?, abstract=?, authors=?, journal_id=?, journal_name=?, published_date=?,
                published_year=?, landing_url=?, oa_status=?, oa_pdf_url=?, source_api=?,
                raw_metadata=?, updated_at=?
            WHERE doi=?
            """,
            payload[1:] + (doi,),
        )
        return False
    conn.execute(
        """
        INSERT INTO papers (
            doi, title, abstract, authors, journal_id, journal_name, published_date,
            published_year, landing_url, oa_status, oa_pdf_url, source_api, raw_metadata,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )
    return True


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
        works = await OpenAlexClient(settings.openalex_mailto).works_by_issn(issn, date_from, date_to)
        if not works:
            works = await CrossrefClient(settings.openalex_mailto).works_by_issn(issn, date_from, date_to)

        keywords = json_loads(journal.get("keywords"), [])
        found = 0
        new_count = 0
        unpaywall = UnpaywallClient(settings.unpaywall_email)
        with get_conn() as conn:
            for work in works:
                if not matches_keywords(work, keywords):
                    continue
                found += 1
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
                SET status='success', papers_found=?, papers_new=?, finished_at=?
                WHERE id=?
                """,
                (found, new_count, now_iso(), job_id),
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

