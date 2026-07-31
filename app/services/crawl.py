import asyncio
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
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
NON_RESEARCH_WORK_TYPES = {
    "component",
    "editorial",
    "erratum",
    "journal",
    "paratext",
    "peer-review",
    "reference-entry",
    "retraction",
}


@dataclass
class CrawlCandidateBatch:
    job_id: int
    journal_id: int
    journal: dict[str, Any] = field(default_factory=dict)
    search_history_id: Optional[int] = None
    search_terms: list[str] = field(default_factory=list)
    found: int = 0
    filtered: int = 0
    candidates: list[dict[str, Any]] = field(default_factory=list)
    source_warning: Optional[str] = None
    error: Optional[str] = None


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


def work_type(work: dict[str, Any]) -> str:
    direct = normalize_text(work.get("work_type"))
    if direct:
        return direct
    raw_metadata = work.get("raw_metadata")
    if isinstance(raw_metadata, dict):
        return normalize_text(raw_metadata.get("type"))
    return ""


def is_research_work(work: dict[str, Any]) -> bool:
    return work_type(work) not in NON_RESEARCH_WORK_TYPES


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
        existing = conn.execute("SELECT id, abstract, authors FROM papers WHERE doi = ?", (doi,)).fetchone()
    elif dedupe_key:
        existing = conn.execute(
            "SELECT id, abstract, authors FROM papers WHERE dedupe_key = ?",
            (dedupe_key,),
        ).fetchone()
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
        abstract_value = payload[2] or optional_text(existing["abstract"], "")
        authors_value = payload[3] if json_list(work.get("authors")) else optional_text(existing["authors"], "[]")
        update_payload = (payload[1], abstract_value, authors_value) + payload[4:]
        conn.execute(
            """
            UPDATE papers
            SET title=?, abstract=?, authors=?, journal_id=?, journal_name=?, published_date=?,
                published_year=?, landing_url=?, oa_status=?, oa_pdf_url=?, source_api=?,
                dedupe_key=?, raw_metadata=?, updated_at=?
            WHERE id=?
            """,
            update_payload + (existing["id"],),
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


async def prepare_crawl_job(
    job_id: int,
    journal_id: int,
    date_from: str,
    date_to: str,
    search_terms: Any = None,
    search_mode: str = "or",
    max_results: int = 50,
) -> CrawlCandidateBatch:
    settings = get_settings()
    batch = CrawlCandidateBatch(
        job_id=job_id,
        journal_id=journal_id,
        search_terms=normalize_search_terms(search_terms),
    )
    with get_conn() as conn:
        conn.execute(
            "UPDATE crawl_jobs SET status='running', started_at=? WHERE id=?",
            (now_iso(), job_id),
        )
        job_row = conn.execute(
            "SELECT search_history_id FROM crawl_jobs WHERE id=?",
            (job_id,),
        ).fetchone()
        batch.search_history_id = (
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
            batch.error = "journal not found"
            return batch
        batch.journal = dict_from_row(journal_row)

    try:
        issn = optional_text(batch.journal.get("issn_electronic")) or optional_text(
            batch.journal.get("issn_print")
        )
        if not issn:
            raise RuntimeError("journal has no ISSN")
        candidate_limit = min(max(max_results, 1) * 2, 200) if batch.search_terms else None
        works, batch.source_warning = await fetch_metadata_works(
            settings,
            issn,
            date_from,
            date_to,
            search_terms=batch.search_terms,
            search_mode=search_mode,
            result_limit=candidate_limit,
        )

        batch.found = len(works)
        for work in works:
            if not is_research_work(work):
                batch.filtered += 1
                continue
            if not matches_search_terms(work, batch.search_terms, search_mode):
                batch.filtered += 1
                continue
            batch.candidates.append(work)
        return batch
    except Exception as exc:
        batch.error = str(exc)
        with get_conn() as conn:
            conn.execute(
                "UPDATE crawl_jobs SET status='failed', error=?, finished_at=? WHERE id=?",
                (batch.error, now_iso(), job_id),
            )
        return batch


def candidate_identity(journal: dict[str, Any], work: dict[str, Any]) -> str:
    doi = normalize_doi(work.get("doi"))
    if doi:
        return f"doi:{doi}"
    dedupe_key = build_dedupe_key(journal, work)
    if dedupe_key:
        return dedupe_key
    return "|".join(
        [
            str(journal.get("id") or ""),
            normalize_text(work.get("title")),
            normalize_text(work.get("published_date") or work.get("published_year")),
        ]
    )


def select_balanced_candidates(
    batches: list[CrawlCandidateBatch],
    max_results: int,
) -> dict[int, list[dict[str, Any]]]:
    """Round-robin journals while preserving provider relevance within each journal."""
    limit = max(0, max_results)
    selected = {batch.job_id: [] for batch in batches}
    cursors = {batch.job_id: 0 for batch in batches}
    seen: set[str] = set()
    eligible = sorted((batch for batch in batches if not batch.error), key=lambda batch: batch.job_id)

    while sum(len(items) for items in selected.values()) < limit:
        made_progress = False
        for batch in eligible:
            candidates = batch.candidates
            cursor = cursors[batch.job_id]
            while cursor < len(candidates):
                work = candidates[cursor]
                cursor += 1
                identity = candidate_identity(batch.journal, work)
                if identity and identity in seen:
                    continue
                if identity:
                    seen.add(identity)
                selected[batch.job_id].append(work)
                made_progress = True
                break
            cursors[batch.job_id] = cursor
            if sum(len(items) for items in selected.values()) >= limit:
                break
        if not made_progress:
            break

    for batch in batches:
        batch.filtered += len(batch.candidates) - len(selected[batch.job_id])
    return selected


async def enrich_missing_abstract(
    work: dict[str, Any],
    crossref: CrossrefClient,
) -> tuple[dict[str, Any], Optional[str]]:
    enriched = dict(work)
    if optional_text(enriched.get("abstract")) or enriched.get("source_api") == "crossref":
        return enriched, None
    doi = normalize_doi(enriched.get("doi"))
    if not doi:
        return enriched, None
    try:
        fallback = await crossref.work_by_doi(doi)
    except Exception as exc:
        return enriched, str(exc)
    if not fallback:
        return enriched, None

    abstract = optional_text(fallback.get("abstract"))
    if abstract:
        enriched["abstract"] = abstract
    if not json_list(enriched.get("authors")) and json_list(fallback.get("authors")):
        enriched["authors"] = fallback["authors"]
    if not optional_text(enriched.get("landing_url")) and optional_text(fallback.get("landing_url")):
        enriched["landing_url"] = fallback["landing_url"]
    raw_metadata = dict(json_object(enriched.get("raw_metadata")))
    raw_metadata["crossref_enrichment"] = json_object(fallback.get("raw_metadata"))
    enriched["raw_metadata"] = raw_metadata
    return enriched, None


async def finalize_crawl_batch(
    batch: CrawlCandidateBatch,
    accepted_candidates: list[dict[str, Any]],
) -> None:
    if batch.error:
        return
    settings = get_settings()
    unpaywall = UnpaywallClient(settings.unpaywall_email, **unpaywall_client_options(settings))
    crossref = None
    accepted_works = []
    enrichment_errors = []
    for original_work in accepted_candidates:
        work = original_work
        enrichment_error = None
        needs_crossref = (
            not optional_text(original_work.get("abstract"))
            and original_work.get("source_api") != "crossref"
            and bool(normalize_doi(original_work.get("doi")))
        )
        if needs_crossref:
            if crossref is None:
                crossref = CrossrefClient(settings.openalex_mailto, **academic_client_options(settings))
            work, enrichment_error = await enrich_missing_abstract(original_work, crossref)
        if enrichment_error:
            enrichment_errors.append(enrichment_error)
        oa = {"oa_status": "unknown", "oa_pdf_url": None}
        normalized_doi = normalize_doi(work.get("doi"))
        if normalized_doi:
            try:
                oa = await unpaywall.resolve(normalized_doi)
            except Exception as exc:
                oa = {"oa_status": "unknown", "oa_pdf_url": None, "error": str(exc)}
        accepted_works.append((work, oa))

    # Keep network awaits outside the SQLite transaction. Parallel journal
    # jobs can enrich concurrently, then each journal writes atomically.
    new_count = 0
    classification_errors = []
    with get_conn() as conn:
        for work, oa in accepted_works:
            created, paper_id = upsert_paper_record(
                conn,
                batch.journal,
                work,
                oa,
                library_status="preview" if batch.search_history_id is not None else "saved",
            )
            if created:
                new_count += 1
            if batch.search_history_id is not None:
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
                        batch.search_history_id,
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
        job_error = batch.source_warning
        if enrichment_errors:
            message = f"metadata enrichment failed for {len(enrichment_errors)} paper(s)"
            job_error = f"{job_error}; {message}" if job_error else message
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
            (batch.found, batch.filtered, new_count, job_error, now_iso(), batch.job_id),
        )


async def run_crawl_job(
    job_id: int,
    journal_id: int,
    date_from: str,
    date_to: str,
    search_terms: Any = None,
    search_mode: str = "or",
    max_results: int = 50,
) -> None:
    batch = await prepare_crawl_job(
        job_id,
        journal_id,
        date_from,
        date_to,
        search_terms,
        search_mode,
        max_results,
    )
    if batch.error:
        return
    accepted_candidates = batch.candidates
    if batch.search_history_id is not None or batch.search_terms:
        accepted_candidates = accepted_candidates[:max_results]
        batch.filtered += len(batch.candidates) - len(accepted_candidates)
    await finalize_crawl_batch(batch, accepted_candidates)


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


async def run_search_crawl_jobs(
    task_args: list[tuple[Any, ...]],
    max_results: int,
    *,
    max_concurrency: Optional[int] = None,
) -> None:
    """Fetch every journal first, then select a deterministic balanced global batch."""
    concurrency = get_settings().crawl_max_concurrency if max_concurrency is None else max_concurrency
    if concurrency < 1:
        raise ValueError("max_concurrency must be at least 1")
    semaphore = asyncio.Semaphore(concurrency)

    async def prepare_one(args: tuple[Any, ...]) -> CrawlCandidateBatch:
        async with semaphore:
            return await prepare_crawl_job(*args)

    batches = await asyncio.gather(*(prepare_one(args) for args in task_args))
    selected = select_balanced_candidates(batches, max_results)

    async def finalize_one(batch: CrawlCandidateBatch) -> None:
        async with semaphore:
            await finalize_crawl_batch(batch, selected[batch.job_id])

    await asyncio.gather(*(finalize_one(batch) for batch in batches))


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
