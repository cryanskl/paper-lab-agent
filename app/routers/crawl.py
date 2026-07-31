import hashlib
import json
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel, Field, field_validator, model_validator

from app.db import dict_from_row, get_conn
from app.errors import AppError, CrawlAsyncJobResponse, page
from app.services.crawl import (
    create_jobs,
    normalize_search_terms,
    resolve_job_specs,
    run_crawl_job,
    run_crawl_jobs,
    run_search_crawl_jobs,
)
from app.services.search_preview import decide_rollback_action
from app.utils import json_dumps, json_loads, now_iso

router = APIRouter(prefix="/crawl", tags=["crawl"])


ALLOWED_PERIODS = {"manual", "daily", "weekly", "monthly"}
SEARCH_CACHE_TTL_HOURS = 24


class CrawlJobJournalResponse(BaseModel):
    id: int
    name: str
    issn_print: Optional[str] = None
    issn_electronic: Optional[str] = None
    active: bool


class CrawlJobDiagnosticsResponse(BaseModel):
    journal_id: Optional[int] = None
    journal_name: Optional[str] = None
    period: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    status: Optional[str] = None
    papers_found: int
    papers_filtered: int
    papers_new: int
    papers_accepted: int
    papers_existing: int
    outcome: str
    keyword_mode: str
    keyword_terms: list[str]
    search_mode: Optional[str] = None
    search_terms: list[str]
    max_results: Optional[int] = None
    error: Optional[str] = None


class CrawlJobDetailResponse(BaseModel):
    id: int
    journal_id: Optional[int] = None
    period: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    status: str
    papers_found: int
    papers_filtered: int
    papers_new: int
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    created_at: str
    journal: Optional[CrawlJobJournalResponse] = None
    diagnostics: CrawlJobDiagnosticsResponse


class CrawlJobListResponse(BaseModel):
    items: list[CrawlJobDetailResponse]
    total: int
    page: int
    page_size: int


def crawl_job_outcome(status: Optional[str], papers_found: int, papers_filtered: int, papers_new: int) -> str:
    normalized_status = (status or "").strip().lower()
    if normalized_status in {"pending", "running", "failed"}:
        return normalized_status
    papers_accepted = max(papers_found - papers_filtered, 0)
    if papers_found == 0:
        return "no_source_results"
    if papers_accepted == 0:
        return "all_filtered"
    if papers_new > 0:
        return "new_papers"
    return "accepted_existing_only"


def serialize_job_detail(job: dict, journal: Optional[dict]) -> dict:
    journal_summary = None
    if journal:
        journal_summary = {
            "id": journal["id"],
            "name": journal["name"],
            "issn_print": journal.get("issn_print"),
            "issn_electronic": journal.get("issn_electronic"),
            "active": bool(journal.get("active")),
        }
    papers_accepted = max((job.get("papers_found") or 0) - (job.get("papers_filtered") or 0), 0)
    papers_new = job.get("papers_new") or 0
    papers_found = job.get("papers_found") or 0
    papers_filtered = job.get("papers_filtered") or 0
    search_terms = json_loads(job.get("search_terms"), [])
    if not isinstance(search_terms, list):
        search_terms = []
    diagnostics = {
        "journal_id": job.get("journal_id"),
        "journal_name": journal.get("name") if journal else None,
        "period": job.get("period"),
        "date_from": job.get("date_from"),
        "date_to": job.get("date_to"),
        "status": job.get("status"),
        "papers_found": papers_found,
        "papers_filtered": papers_filtered,
        "papers_new": papers_new,
        "papers_accepted": papers_accepted,
        "papers_existing": max(papers_accepted - papers_new, 0),
        "outcome": crawl_job_outcome(job.get("status"), papers_found, papers_filtered, papers_new),
        "keyword_mode": "disabled",
        "keyword_terms": [],
        "search_mode": job.get("search_mode"),
        "search_terms": search_terms,
        "max_results": job.get("max_results"),
        "error": job.get("error"),
    }
    return job | {"journal": journal_summary, "diagnostics": diagnostics}


class CrawlRunResponse(BaseModel):
    jobs: list[CrawlAsyncJobResponse]
    search_id: Optional[int] = None
    decision_status: Optional[str] = None
    cache_hit: bool = False
    cache_ttl_hours: int = SEARCH_CACHE_TTL_HOURS
    result_count: int = 0


class SearchDecisionResponse(BaseModel):
    search_id: int
    decision_status: str
    result_count: int
    new_result_count: int
    saved_count: int = 0
    removed_count: int = 0
    preserved_count: int = 0


class CrawlRunIn(BaseModel):
    journal_ids: Optional[list[int]] = None
    period: str = "manual"
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    search_query: Optional[str] = None
    search_terms: Optional[list[str]] = None
    search_mode: str = "or"
    max_results: int = Field(50, ge=1, le=100)
    force_refresh: bool = False

    @field_validator("journal_ids")
    @classmethod
    def journal_ids_must_be_non_empty_positive_ids(cls, value: Optional[list[int]]) -> Optional[list[int]]:
        if value is None:
            return None
        if not value:
            raise ValueError("journal_ids must not be empty")
        if any(item <= 0 for item in value):
            raise ValueError("journal_ids must be positive integers")
        return value

    @field_validator("period")
    @classmethod
    def period_must_be_supported(cls, value: str) -> str:
        if value not in ALLOWED_PERIODS:
            raise ValueError("period must be one of manual, daily, weekly, monthly")
        return value

    @field_validator("date_from", "date_to")
    @classmethod
    def dates_must_be_iso8601(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        date.fromisoformat(value)
        return value

    @field_validator("search_query")
    @classmethod
    def search_query_must_be_reasonable(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            return None
        if len(normalized) > 300:
            raise ValueError("search_query must be at most 300 characters")
        return normalized

    @field_validator("search_terms")
    @classmethod
    def search_terms_must_be_reasonable(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        if value is None:
            return None
        normalized = normalize_search_terms(value)
        if not normalized:
            raise ValueError("search_terms must contain at least one non-empty term")
        if len(normalized) > 20:
            raise ValueError("search_terms must contain at most 20 terms")
        if any(len(term) > 100 for term in normalized):
            raise ValueError("each search term must be at most 100 characters")
        if sum(len(term) for term in normalized) > 300:
            raise ValueError("search_terms must be at most 300 characters in total")
        return normalized

    @field_validator("search_mode")
    @classmethod
    def search_mode_must_be_supported(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"or", "and"}:
            raise ValueError("search_mode must be 'or' or 'and'")
        return normalized

    @model_validator(mode="after")
    def date_range_must_be_ordered(self) -> "CrawlRunIn":
        if self.date_from and self.date_to and date.fromisoformat(self.date_from) > date.fromisoformat(self.date_to):
            raise ValueError("date_from must be before or equal to date_to")
        return self


def effective_search(body: CrawlRunIn) -> tuple[list[str], str]:
    if body.search_terms:
        return body.search_terms, body.search_mode
    if body.search_query:
        return body.search_query.split(), "and"
    return [], body.search_mode


def search_cache_key(
    terms: list[str],
    mode: str,
    specs: list[dict[str, Any]],
    max_results: int,
) -> str:
    payload = {
        "terms": [term.casefold() for term in terms],
        "mode": mode,
        "scope": sorted(
            [
                {
                    "journal_id": spec["journal_id"],
                    "date_from": spec["date_from"],
                    "date_to": spec["date_to"],
                }
                for spec in specs
            ],
            key=lambda item: item["journal_id"],
        ),
        "max_results": max_results,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def run_search_jobs(search_history_id: int, task_args_list: list[tuple[Any, ...]]) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE search_history SET status='running' WHERE id=?",
            (search_history_id,),
        )
    try:
        with get_conn() as conn:
            history = conn.execute(
                "SELECT max_results FROM search_history WHERE id=?",
                (search_history_id,),
            ).fetchone()
        max_results = int((history["max_results"] if history else 0) or 0)
        await run_search_crawl_jobs(task_args_list, max_results)
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT status, papers_found, papers_filtered, error
                FROM crawl_jobs
                WHERE search_history_id=?
                """,
                (search_history_id,),
            ).fetchall()
            failed = [row for row in rows if row["status"] != "success"]
            result_summary = conn.execute(
                """
                SELECT COUNT(*) AS result_count,
                       COALESCE(SUM(was_new), 0) AS new_result_count
                FROM search_results
                WHERE search_history_id=?
                """,
                (search_history_id,),
            ).fetchone()
            result_count = int(result_summary["result_count"] or 0)
            new_result_count = int(result_summary["new_result_count"] or 0)
            status = "failed" if failed else "success"
            error = "; ".join(str(row["error"]) for row in failed if row["error"]) or None
            conn.execute(
                """
                UPDATE search_history
                SET status=?, result_count=?, new_result_count=?, error=?, finished_at=?
                WHERE id=?
                """,
                (status, result_count, new_result_count, error, now_iso(), search_history_id),
            )
    except Exception as exc:
        with get_conn() as conn:
            conn.execute(
                """
                UPDATE search_history
                SET status='failed', error=?, finished_at=?
                WHERE id=?
                """,
                (str(exc), now_iso(), search_history_id),
            )


@router.post("/run", status_code=202, response_model=CrawlRunResponse)
def run_crawl(background_tasks: BackgroundTasks, body: Optional[CrawlRunIn] = None) -> dict:
    body = body or CrawlRunIn()
    terms, search_mode = effective_search(body)
    try:
        specs = resolve_job_specs(body.journal_ids, body.date_from, body.date_to)
    except LookupError as exc:
        raise AppError(404, "journal_not_found", str(exc))
    except ValueError as exc:
        raise AppError(400, "invalid_crawl_date_range", str(exc))
    if not specs:
        raise AppError(404, "no_active_journals", "No active journals matched crawl request")

    search_history_id = None
    cache_key = None
    if terms and body.period == "manual":
        cache_key = search_cache_key(terms, search_mode, specs, body.max_results)
        if not body.force_refresh:
            with get_conn() as conn:
                cached = conn.execute(
                    """
                    SELECT id, result_count, decision_status
                    FROM search_history
                    WHERE cache_key=? AND status='success'
                      AND decision_status != 'discarded'
                      AND finished_at >= datetime('now', ?)
                    ORDER BY finished_at DESC, id DESC
                    LIMIT 1
                    """,
                    (cache_key, f"-{SEARCH_CACHE_TTL_HOURS} hours"),
                ).fetchone()
            if cached:
                return {
                    "jobs": [],
                    "search_id": cached["id"],
                    "decision_status": cached["decision_status"],
                    "cache_hit": True,
                    "cache_ttl_hours": SEARCH_CACHE_TTL_HOURS,
                    "result_count": cached["result_count"] or 0,
                }
        journal_ids = sorted(spec["journal_id"] for spec in specs)
        with get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO search_history (
                    cache_key, query_text, search_terms, search_mode, journal_ids,
                    date_from, date_to, max_results, status, decision_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'preview')
                """,
                (
                    cache_key,
                    ", ".join(terms),
                    json_dumps(terms),
                    search_mode,
                    json_dumps(journal_ids),
                    min(spec["date_from"] for spec in specs),
                    max(spec["date_to"] for spec in specs),
                    body.max_results,
                ),
            )
            search_history_id = cursor.lastrowid

    try:
        if terms:
            jobs = create_jobs(
                body.journal_ids,
                body.period,
                body.date_from,
                body.date_to,
                search_terms=terms,
                search_mode=search_mode,
                max_results=body.max_results,
                search_history_id=search_history_id,
            )
        else:
            jobs = create_jobs(body.journal_ids, body.period, body.date_from, body.date_to)
    except (LookupError, ValueError) as exc:
        if search_history_id is not None:
            with get_conn() as conn:
                conn.execute(
                    "UPDATE search_history SET status='failed', error=?, finished_at=? WHERE id=?",
                    (str(exc), now_iso(), search_history_id),
                )
        if isinstance(exc, LookupError):
            raise AppError(404, "journal_not_found", str(exc))
        raise AppError(400, "invalid_crawl_date_range", str(exc))
    task_args_list = []
    for job in jobs:
        task_args = (job["job_id"], job["journal_id"], job["date_from"], job["date_to"])
        if terms:
            task_args += (terms, search_mode, body.max_results)
        task_args_list.append(task_args)
    if search_history_id is not None:
        with get_conn() as conn:
            conn.execute(
                "UPDATE search_history SET job_ids=? WHERE id=?",
                (json_dumps([job["job_id"] for job in jobs]), search_history_id),
            )
        background_tasks.add_task(run_search_jobs, search_history_id, task_args_list)
    else:
        background_tasks.add_task(run_crawl_jobs, task_args_list, runner=run_crawl_job)
    return {
        "jobs": [
            {
                "job_id": job["job_id"],
                "journal_id": job["journal_id"],
                "period": body.period,
                "date_from": job["date_from"],
                "date_to": job["date_to"],
                "status": "pending",
            }
            for job in jobs
        ],
        "search_id": search_history_id,
        "decision_status": "preview" if search_history_id is not None else None,
        "cache_hit": False,
        "cache_ttl_hours": SEARCH_CACHE_TTL_HOURS,
        "result_count": 0,
    }


def search_result_counts(conn, search_id: int) -> tuple[int, int]:
    row = conn.execute(
        """
        SELECT COUNT(*) AS result_count, COALESCE(SUM(was_new), 0) AS new_result_count
        FROM search_results
        WHERE search_history_id=?
        """,
        (search_id,),
    ).fetchone()
    return int(row["result_count"] or 0), int(row["new_result_count"] or 0)


@router.post("/searches/{search_id}/save", response_model=SearchDecisionResponse)
def save_search_results(search_id: int) -> dict:
    with get_conn() as conn:
        history = conn.execute("SELECT * FROM search_history WHERE id=?", (search_id,)).fetchone()
        if not history:
            raise AppError(404, "search_not_found", "Search batch not found")
        if history["status"] != "success":
            raise AppError(409, "search_not_ready", "Search batch is not complete")
        if history["decision_status"] == "discarded":
            raise AppError(409, "search_discarded", "Discarded search batch cannot be saved")
        result_count, new_result_count = search_result_counts(conn, search_id)
        saved_count = conn.execute(
            """
            SELECT COUNT(DISTINCT p.id) AS n
            FROM search_results sr
            JOIN papers p ON p.id=sr.paper_id
            WHERE sr.search_history_id=? AND p.library_status='preview'
            """,
            (search_id,),
        ).fetchone()["n"]
        conn.execute(
            """
            UPDATE papers
            SET library_status='saved', updated_at=?
            WHERE id IN (
                SELECT paper_id
                FROM search_results
                WHERE search_history_id=? AND paper_id IS NOT NULL
            )
            """,
            (now_iso(), search_id),
        )
        conn.execute(
            """
            UPDATE search_results
            SET result_status=CASE WHEN was_new=1 THEN 'saved' ELSE 'existing' END,
                updated_at=?
            WHERE search_history_id=?
            """,
            (now_iso(), search_id),
        )
        conn.execute(
            """
            UPDATE search_history
            SET decision_status='saved', new_result_count=?, saved_at=?, discarded_at=NULL
            WHERE id=?
            """,
            (new_result_count, now_iso(), search_id),
        )
    return {
        "search_id": search_id,
        "decision_status": "saved",
        "result_count": result_count,
        "new_result_count": new_result_count,
        "saved_count": int(saved_count or 0),
        "removed_count": 0,
        "preserved_count": result_count - int(saved_count or 0),
    }


@router.delete("/searches/{search_id}", response_model=SearchDecisionResponse)
def discard_search_results(search_id: int) -> dict:
    with get_conn() as conn:
        history = conn.execute("SELECT * FROM search_history WHERE id=?", (search_id,)).fetchone()
        if not history:
            raise AppError(404, "search_not_found", "Search batch not found")
        if history["status"] != "success":
            raise AppError(409, "search_not_ready", "Search batch is not complete")
        result_count, new_result_count = search_result_counts(conn, search_id)
        if history["decision_status"] == "discarded":
            status_rows = conn.execute(
                """
                SELECT result_status, COUNT(*) AS n
                FROM search_results
                WHERE search_history_id=?
                GROUP BY result_status
                """,
                (search_id,),
            ).fetchall()
            status_counts = {row["result_status"]: int(row["n"]) for row in status_rows}
            return {
                "search_id": search_id,
                "decision_status": "discarded",
                "result_count": result_count,
                "new_result_count": new_result_count,
                "saved_count": 0,
                "removed_count": status_counts.get("removed", 0),
                "preserved_count": result_count - status_counts.get("removed", 0),
            }

        removed_count = 0
        preserved_count = 0
        results = conn.execute(
            """
            SELECT id, paper_id, was_new
            FROM search_results
            WHERE search_history_id=?
            ORDER BY id
            """,
            (search_id,),
        ).fetchall()
        for result in results:
            result_id = int(result["id"])
            paper_id = result["paper_id"]
            if not result["was_new"] or paper_id is None:
                preserved_count += 1
                conn.execute(
                    "UPDATE search_results SET result_status='preserved', updated_at=? WHERE id=?",
                    (now_iso(), result_id),
                )
                continue
            paper = conn.execute(
                "SELECT library_status FROM papers WHERE id=?",
                (paper_id,),
            ).fetchone()
            if not paper:
                removed_count += 1
                conn.execute(
                    "UPDATE search_results SET result_status='removed', updated_at=? WHERE id=?",
                    (now_iso(), result_id),
                )
                continue
            has_document = (
                conn.execute("SELECT 1 FROM documents WHERE paper_id=? LIMIT 1", (paper_id,)).fetchone() is not None
            )
            references = conn.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN h.decision_status='saved' THEN 1 ELSE 0 END), 0) AS saved_count,
                    COALESCE(SUM(CASE WHEN h.decision_status='preview' THEN 1 ELSE 0 END), 0) AS preview_count
                FROM search_results sr
                JOIN search_history h ON h.id=sr.search_history_id
                WHERE sr.paper_id=? AND sr.search_history_id!=?
                  AND h.status='success' AND h.decision_status!='discarded'
                """,
                (paper_id, search_id),
            ).fetchone()
            action = decide_rollback_action(
                has_document=has_document,
                has_other_saved_search=int(references["saved_count"] or 0) > 0,
                has_other_preview_search=int(references["preview_count"] or 0) > 0,
            )
            if action == "remove":
                conn.execute("DELETE FROM papers WHERE id=?", (paper_id,))
                removed_count += 1
                result_status = "removed"
            else:
                next_library_status = "saved" if action == "preserve_saved" else "preview"
                conn.execute(
                    "UPDATE papers SET library_status=?, updated_at=? WHERE id=?",
                    (next_library_status, now_iso(), paper_id),
                )
                preserved_count += 1
                result_status = "preserved"
            conn.execute(
                "UPDATE search_results SET result_status=?, updated_at=? WHERE id=?",
                (result_status, now_iso(), result_id),
            )
        conn.execute(
            """
            UPDATE search_history
            SET decision_status='discarded', discarded_at=?, saved_at=NULL
            WHERE id=?
            """,
            (now_iso(), search_id),
        )
    return {
        "search_id": search_id,
        "decision_status": "discarded",
        "result_count": result_count,
        "new_result_count": new_result_count,
        "saved_count": 0,
        "removed_count": removed_count,
        "preserved_count": preserved_count,
    }


@router.get("/jobs", response_model=CrawlJobListResponse)
def list_jobs(page_num: int = Query(1, alias="page", ge=1), page_size: int = Query(20, ge=1, le=100)) -> dict:
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM crawl_jobs").fetchone()["n"]
        rows = conn.execute("SELECT * FROM crawl_jobs ORDER BY id DESC LIMIT ? OFFSET ?", (page_size, offset)).fetchall()
        jobs = []
        for row in rows:
            journal_row = None
            if row["journal_id"] is not None:
                journal_row = conn.execute("SELECT * FROM journals WHERE id=?", (row["journal_id"],)).fetchone()
            jobs.append(serialize_job_detail(dict_from_row(row), dict_from_row(journal_row) if journal_row else None))
    return page(jobs, total, page_num, page_size)


@router.get("/jobs/{job_id}", response_model=CrawlJobDetailResponse)
def get_job(job_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM crawl_jobs WHERE id=?", (job_id,)).fetchone()
        journal_row = None
        if row and row["journal_id"] is not None:
            journal_row = conn.execute("SELECT * FROM journals WHERE id=?", (row["journal_id"],)).fetchone()
    if not row:
        raise AppError(404, "crawl_job_not_found", "Crawl job not found")
    return serialize_job_detail(dict_from_row(row), dict_from_row(journal_row) if journal_row else None)
