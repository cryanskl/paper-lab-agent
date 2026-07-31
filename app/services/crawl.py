import asyncio
import hashlib
import re
import unicodedata
from datetime import date
from typing import Any, Awaitable, Callable, Optional

from app.clients.crossref import CrossrefClient
from app.clients.openalex import OpenAlexClient
from app.clients.unpaywall import UnpaywallClient, oa_status, web_url
from app.config import get_settings
from app.db import dict_from_row, get_conn
from app.services.classification import get_classifier
from app.utils import json_dumps, json_loads, now_iso, today_iso

SUBSCRIPT_DIGIT_TRANSLATION = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
SEARCH_TERM_SPLIT_RE = re.compile(r"[\n,，;；]+")


def normalize_text(value: Any) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"\s+", " ", normalized.strip().lower())


def normalize_keyword_text(value: Any) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).translate(SUBSCRIPT_DIGIT_TRANSLATION)
    text = re.sub(r"[^0-9a-zA-Z]+", " ", normalized.strip().lower())
    return re.sub(r"\s+", " ", text).strip()


def normalize_keyword_config(keyword_config: Any) -> tuple[str, list[str]]:
    if isinstance(keyword_config, dict):
        mode = str(keyword_config.get("mode") or "or").strip().lower()
        terms = keyword_config.get("terms") or keyword_config.get("keywords") or []
    else:
        mode = "or"
        terms = keyword_config or []
    if isinstance(terms, str):
        terms = [terms]
    normalized_terms = [normalize_keyword_text(term) for term in terms if normalize_keyword_text(term)]
    return ("and" if mode == "and" else "or", normalized_terms)


def normalize_search_terms(value: Any) -> list[str]:
    if value is None:
        return []
    raw_terms = value if isinstance(value, list) else SEARCH_TERM_SPLIT_RE.split(str(value))
    normalized_terms = []
    seen = set()
    for item in raw_terms:
        if not isinstance(item, str):
            continue
        term = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", item).strip())
        key = term.casefold()
        if not term or key in seen:
            continue
        seen.add(key)
        normalized_terms.append(term)
    return normalized_terms


def build_provider_search_query(search_terms: Any, search_mode: str = "or") -> Optional[str]:
    terms = normalize_search_terms(search_terms)
    if not terms:
        return None
    operator = " AND " if str(search_mode).strip().lower() == "and" else " OR "
    operands = []
    for term in terms:
        escaped = term.replace("\\", "\\\\").replace('"', '\\"')
        operands.append(f'"{escaped}"' if " " in escaped else escaped)
    return operator.join(operands)


def matches_search_terms(work: dict[str, Any], search_terms: Any, search_mode: str = "or") -> bool:
    terms = [normalize_keyword_text(term) for term in normalize_search_terms(search_terms)]
    terms = [term for term in terms if term]
    if not terms:
        return True
    authors = work.get("authors") or []
    if isinstance(authors, list):
        author_text = " ".join(
            str(author.get("name") or author.get("display_name") or "")
            if isinstance(author, dict)
            else str(author)
            for author in authors
        )
    else:
        author_text = str(authors)
    haystack = normalize_keyword_text(
        f"{work.get('title') or ''}\n{work.get('abstract') or ''}\n"
        f"{work.get('doi') or ''}\n{author_text}"
    )
    padded_haystack = f" {haystack} "
    checks = [f" {term} " in padded_haystack for term in terms]
    if str(search_mode).strip().lower() == "and":
        return all(checks)
    return any(checks)


def matches_keywords(work: dict[str, Any], keywords: Any) -> bool:
    mode, terms = normalize_keyword_config(keywords)
    if not terms:
        return True
    haystack = normalize_keyword_text(f"{work.get('title') or ''}\n{work.get('abstract') or ''}")
    padded_haystack = f" {haystack} "
    if mode == "and":
        return all(f" {term} " in padded_haystack for term in terms)
    return any(f" {term} " in padded_haystack for term in terms)


def matches_search_query(work: dict[str, Any], search_query: Optional[str]) -> bool:
    normalized_query = normalize_keyword_text(search_query)
    if not normalized_query:
        return True
    terms = normalized_query.split()
    authors = work.get("authors") or []
    if isinstance(authors, list):
        author_text = " ".join(
            str(author.get("name") or author.get("display_name") or "")
            if isinstance(author, dict)
            else str(author)
            for author in authors
        )
    else:
        author_text = str(authors)
    haystack = normalize_keyword_text(
        f"{work.get('title') or ''}\n{work.get('abstract') or ''}\n"
        f"{work.get('doi') or ''}\n{author_text}"
    )
    padded_haystack = f" {haystack} "
    return all(f" {term} " in padded_haystack for term in terms)


def optional_text(value: Any, default: Optional[str] = None) -> Optional[str]:
    if isinstance(value, str):
        text = value.strip()
        if text:
            return text
    return default


def optional_int(value: Any) -> Optional[int]:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def paper_raw_metadata(work: dict[str, Any], oa: dict[str, Any]) -> dict[str, Any]:
    raw_metadata = dict(json_object(work.get("raw_metadata")))
    if isinstance(oa.get("raw"), dict):
        raw_metadata["unpaywall"] = oa["raw"]
    if oa.get("error"):
        raw_metadata["oa_resolution_error"] = str(oa["error"])
    return raw_metadata


def normalize_doi(value: Any) -> Optional[str]:
    doi = normalize_text(optional_text(value))
    if not doi:
        return None
    return (
        doi.removeprefix("https://doi.org/")
        .removeprefix("http://doi.org/")
        .removeprefix("https://dx.doi.org/")
        .removeprefix("http://dx.doi.org/")
        .removeprefix("doi:")
    ).strip()


def build_dedupe_key(journal: dict[str, Any], work: dict[str, Any]) -> Optional[str]:
    doi = normalize_doi(work.get("doi"))
    if doi:
        return f"doi:{doi}"
    title = normalize_text(optional_text(work.get("title")))
    if not title:
        return None
    date_hint = normalize_text(optional_text(work.get("published_date")) or optional_int(work.get("published_year")))
    landing_url = normalize_text(optional_text(work.get("landing_url")))
    if not date_hint and not landing_url:
        return None
    fingerprint = "|".join([str(journal["id"]), title, date_hint, landing_url])
    return f"no-doi:{hashlib.sha256(fingerprint.encode('utf-8')).hexdigest()}"


def upsert_paper_record(
    conn,
    journal: dict[str, Any],
    work: dict[str, Any],
    oa: dict[str, Any],
    *,
    library_status: str = "saved",
) -> tuple[bool, int]:
    doi = normalize_doi(work.get("doi"))
    dedupe_key = build_dedupe_key(journal, work)
    existing = None
    if doi:
        existing = conn.execute("SELECT id FROM papers WHERE doi = ?", (doi,)).fetchone()
    elif dedupe_key:
        existing = conn.execute("SELECT id FROM papers WHERE dedupe_key = ?", (dedupe_key,)).fetchone()
    payload = (
        doi,
        optional_text(work.get("title"), "Untitled"),
        optional_text(work.get("abstract"), ""),
        json_dumps(json_list(work.get("authors"))),
        journal["id"],
        optional_text(work.get("journal_name"), journal["name"]),
        optional_text(work.get("published_date")),
        optional_int(work.get("published_year")),
        optional_text(work.get("landing_url")),
        oa_status(oa.get("oa_status")),
        web_url(oa.get("oa_pdf_url")),
        optional_text(work.get("source_api")),
        dedupe_key,
        json_dumps(paper_raw_metadata(work, oa)),
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
        return False, existing["id"]
    cursor = conn.execute(
        """
        INSERT INTO papers (
            doi, title, abstract, authors, journal_id, journal_name, published_date,
            published_year, landing_url, oa_status, oa_pdf_url, source_api, dedupe_key, raw_metadata,
            library_status, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload[:-1] + (library_status, payload[-1]),
    )
    return True, cursor.lastrowid


def upsert_paper(conn, journal: dict[str, Any], work: dict[str, Any], oa: dict[str, Any]) -> bool:
    created, _paper_id = upsert_paper_record(conn, journal, work, oa)
    return created


def classify_paper(conn, settings, paper_id: int) -> None:
    row = conn.execute("SELECT title, abstract FROM papers WHERE id=?", (paper_id,)).fetchone()
    if not row:
        return
    categories = [dict_from_row(category_row) for category_row in conn.execute("SELECT * FROM categories").fetchall()]
    text = f"{row['title']} {row['abstract'] or ''}"
    classified = get_classifier(settings).classify(text, categories)
    conn.execute("DELETE FROM paper_categories WHERE paper_id=? AND method='auto'", (paper_id,))
    for item in classified:
        conn.execute(
            """
            INSERT OR IGNORE INTO paper_categories (paper_id, category_id, confidence, method)
            VALUES (?, ?, ?, 'auto')
            """,
            (paper_id, item["category_id"], item["confidence"]),
        )


def academic_client_options(settings) -> dict[str, Any]:
    return {
        "max_retries": settings.academic_api_max_retries,
        "retry_backoff_seconds": settings.academic_api_retry_backoff_seconds,
        "request_interval_seconds": settings.academic_api_request_interval_seconds,
        "timeout": settings.academic_api_timeout_seconds,
    }


def unpaywall_client_options(settings) -> dict[str, Any]:
    return {
        "max_retries": settings.unpaywall_api_max_retries,
        "retry_backoff_seconds": settings.unpaywall_api_retry_backoff_seconds,
        "request_interval_seconds": settings.unpaywall_api_request_interval_seconds,
        "timeout": settings.unpaywall_api_timeout_seconds,
    }


async def fetch_metadata_works(
    settings,
    issn: str,
    date_from: str,
    date_to: str,
    *,
    search_terms: Any = None,
    search_mode: str = "or",
    result_limit: Optional[int] = None,
) -> tuple[list[dict[str, Any]], Optional[str]]:
    client_options = academic_client_options(settings)
    provider_query = build_provider_search_query(search_terms, search_mode)
    request_options: dict[str, Any] = {"max_pages": settings.academic_api_max_pages}
    if provider_query:
        request_options["search_query"] = provider_query
    if result_limit is not None:
        request_options["result_limit"] = result_limit
    openalex_error = None
    openalex_empty = False
    try:
        works = await OpenAlexClient(
            mailto=settings.openalex_mailto,
            api_key=settings.openalex_api_key,
            **client_options,
        ).works_by_issn(issn, date_from, date_to, **request_options)
        if works:
            return works, None
        openalex_empty = True
    except Exception as exc:
        openalex_error = str(exc)

    try:
        works = await CrossrefClient(settings.openalex_mailto, **client_options).works_by_issn(
            issn, date_from, date_to, **request_options
        )
    except Exception as exc:
        if openalex_error:
            raise RuntimeError(f"OpenAlex failed: {openalex_error}; Crossref failed: {exc}") from exc
        if openalex_empty:
            raise RuntimeError(f"OpenAlex returned no works; Crossref failed: {exc}") from exc
        raise
    if openalex_empty:
        return works, "OpenAlex returned no works; used Crossref fallback"
    if openalex_error:
        return works, f"OpenAlex failed; used Crossref fallback: {openalex_error}"
    return works, None


async def run_crawl_job(
    job_id: int,
    journal_id: int,
    date_from: str,
    date_to: str,
    search_terms: Any = None,
    search_mode: str = "or",
    max_results: int = 50,
) -> None:
    settings = get_settings()
    with get_conn() as conn:
        conn.execute(
            "UPDATE crawl_jobs SET status='running', started_at=? WHERE id=?",
            (now_iso(), job_id),
        )
        job_row = conn.execute(
            "SELECT search_history_id FROM crawl_jobs WHERE id=?",
            (job_id,),
        ).fetchone()
        search_history_id = (
            int(job_row["search_history_id"])
            if job_row and job_row["search_history_id"] is not None
            else None
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
        issn = optional_text(journal.get("issn_electronic")) or optional_text(journal.get("issn_print"))
        if not issn:
            raise RuntimeError("journal has no ISSN")
        normalized_search_terms = normalize_search_terms(search_terms)
        candidate_limit = min(max(max_results, 1) * 2, 200) if normalized_search_terms else None
        works, source_warning = await fetch_metadata_works(
            settings,
            issn,
            date_from,
            date_to,
            search_terms=normalized_search_terms,
            search_mode=search_mode,
            result_limit=candidate_limit,
        )

        found = len(works)
        filtered = 0
        new_count = 0
        classification_errors = []
        accepted_candidates = []
        for work in works:
            if not matches_search_terms(work, normalized_search_terms, search_mode):
                filtered += 1
                continue
            if search_history_id is None and normalized_search_terms and len(accepted_candidates) >= max_results:
                filtered += 1
                continue
            accepted_candidates.append(work)

        if search_history_id is not None:
            # Reserve the shared cross-journal budget before OA lookups. This keeps
            # Unpaywall work bounded by max_results even when many journals run in parallel.
            with get_conn() as conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT result_count FROM search_history WHERE id=?",
                    (search_history_id,),
                ).fetchone()
                allocated = int((row["result_count"] if row else 0) or 0)
                remaining = max(max_results - allocated, 0)
                reserved_count = min(len(accepted_candidates), remaining)
                if len(accepted_candidates) > reserved_count:
                    filtered += len(accepted_candidates) - reserved_count
                    accepted_candidates = accepted_candidates[:reserved_count]
                conn.execute(
                    "UPDATE search_history SET result_count=? WHERE id=?",
                    (allocated + reserved_count, search_history_id),
                )

        unpaywall = UnpaywallClient(settings.unpaywall_email, **unpaywall_client_options(settings))
        accepted_works = []
        for work in accepted_candidates:
            oa = {"oa_status": "unknown", "oa_pdf_url": None}
            normalized_doi = normalize_doi(work.get("doi"))
            if normalized_doi:
                try:
                    oa = await unpaywall.resolve(normalized_doi)
                except Exception as exc:
                    oa = {"oa_status": "unknown", "oa_pdf_url": None, "error": str(exc)}
            accepted_works.append((work, oa))

        # Keep network awaits outside the SQLite transaction. Parallel journal
        # jobs can fetch concurrently, then each journal writes atomically.
        with get_conn() as conn:
            for work, oa in accepted_works:
                created, paper_id = upsert_paper_record(
                    conn,
                    journal,
                    work,
                    oa,
                    library_status="preview" if search_history_id is not None else "saved",
                )
                if created:
                    new_count += 1
                if search_history_id is not None:
                    paper_row = conn.execute(
                        "SELECT title, doi, library_status FROM papers WHERE id=?",
                        (paper_id,),
                    ).fetchone()
                    result_status = "preview" if paper_row["library_status"] == "preview" else "existing"
                    conn.execute(
                        """
                        INSERT INTO search_results (
                            search_history_id, paper_id, paper_title, paper_doi,
                            was_new, result_status, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(search_history_id, paper_id) DO UPDATE SET
                            paper_title=excluded.paper_title,
                            paper_doi=excluded.paper_doi,
                            was_new=MAX(search_results.was_new, excluded.was_new),
                            result_status=excluded.result_status,
                            updated_at=excluded.updated_at
                        """,
                        (
                            search_history_id,
                            paper_id,
                            paper_row["title"],
                            paper_row["doi"],
                            int(created),
                            result_status,
                            now_iso(),
                        ),
                    )
                try:
                    classify_paper(conn, settings, paper_id)
                except Exception as exc:
                    classification_errors.append(f"paper {paper_id}: {exc}")
            job_error = source_warning
            if classification_errors:
                message = f"classification failed for {len(classification_errors)} paper(s): " + "; ".join(
                    classification_errors[:3]
                )
                job_error = f"{job_error}; {message}" if job_error else message
            conn.execute(
                """
                UPDATE crawl_jobs
                SET status='success', papers_found=?, papers_filtered=?, papers_new=?, error=?, finished_at=?
                WHERE id=?
                """,
                (found, filtered, new_count, job_error, now_iso(), job_id),
            )
    except Exception as exc:
        with get_conn() as conn:
            conn.execute(
                "UPDATE crawl_jobs SET status='failed', error=?, finished_at=? WHERE id=?",
                (str(exc), now_iso(), job_id),
            )


CrawlJobRunner = Callable[..., Awaitable[None]]


async def run_crawl_jobs(
    task_args: list[tuple[Any, ...]],
    *,
    max_concurrency: Optional[int] = None,
    runner: Optional[CrawlJobRunner] = None,
) -> None:
    """Run journal jobs concurrently while keeping external API load bounded."""
    concurrency = get_settings().crawl_max_concurrency if max_concurrency is None else max_concurrency
    if concurrency < 1:
        raise ValueError("max_concurrency must be at least 1")
    semaphore = asyncio.Semaphore(concurrency)
    job_runner = runner or run_crawl_job

    async def run_one(args: tuple[Any, ...]) -> None:
        async with semaphore:
            await job_runner(*args)

    await asyncio.gather(*(run_one(args) for args in task_args))


def resolve_job_specs(
    journal_ids: Optional[list[int]],
    date_from: Optional[str],
    date_to: Optional[str],
) -> list[dict[str, Any]]:
    date_to = date_to or today_iso()
    with get_conn() as conn:
        if journal_ids:
            requested_ids = list(dict.fromkeys(journal_ids))
            placeholders = ",".join("?" for _ in requested_ids)
            journals = conn.execute(
                f"SELECT * FROM journals WHERE active=1 AND id IN ({placeholders})", tuple(requested_ids)
            ).fetchall()
            found_ids = {row["id"] for row in journals}
            missing_ids = [journal_id for journal_id in requested_ids if journal_id not in found_ids]
            if missing_ids:
                raise LookupError(f"active journals not found: {', '.join(str(journal_id) for journal_id in missing_ids)}")
        else:
            journals = conn.execute("SELECT * FROM journals WHERE active=1").fetchall()
        specs = []
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
            if date.fromisoformat(start) > date.fromisoformat(date_to):
                raise ValueError(f"date_from must be before or equal to date_to for journal {journal['id']}")
            specs.append({"journal_id": journal["id"], "date_from": start, "date_to": date_to})
    return specs


def create_jobs(
    journal_ids: Optional[list[int]],
    period: str,
    date_from: Optional[str],
    date_to: Optional[str],
    *,
    search_terms: Any = None,
    search_mode: Optional[str] = None,
    max_results: Optional[int] = None,
    search_history_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    specs = resolve_job_specs(journal_ids, date_from, date_to)
    with get_conn() as conn:
        jobs = []
        for spec in specs:
            cursor = conn.execute(
                """
                INSERT INTO crawl_jobs (
                    journal_id, period, date_from, date_to, status,
                    search_terms, search_mode, max_results, search_history_id
                )
                VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (
                    spec["journal_id"],
                    period,
                    spec["date_from"],
                    spec["date_to"],
                    json_dumps(normalize_search_terms(search_terms)) if normalize_search_terms(search_terms) else None,
                    search_mode,
                    max_results,
                    search_history_id,
                ),
            )
            jobs.append({"job_id": cursor.lastrowid, **spec})
        return jobs
