from datetime import date
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel, field_validator, model_validator

from app.db import dict_from_row, get_conn
from app.errors import AppError, page
from app.services.crawl import create_jobs, run_crawl_job

router = APIRouter(prefix="/crawl", tags=["crawl"])


ALLOWED_PERIODS = {"manual", "daily", "weekly", "monthly"}


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
    diagnostics = {
        "journal_id": job.get("journal_id"),
        "journal_name": journal.get("name") if journal else None,
        "period": job.get("period"),
        "date_from": job.get("date_from"),
        "date_to": job.get("date_to"),
        "status": job.get("status"),
        "papers_found": job.get("papers_found") or 0,
        "papers_filtered": job.get("papers_filtered") or 0,
        "papers_new": job.get("papers_new") or 0,
        "papers_accepted": max((job.get("papers_found") or 0) - (job.get("papers_filtered") or 0), 0),
        "error": job.get("error"),
    }
    return job | {"journal": journal_summary, "diagnostics": diagnostics}


class CrawlRunIn(BaseModel):
    journal_ids: Optional[list[int]] = None
    period: str = "manual"
    date_from: Optional[str] = None
    date_to: Optional[str] = None

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

    @model_validator(mode="after")
    def date_range_must_be_ordered(self) -> "CrawlRunIn":
        if self.date_from and self.date_to and date.fromisoformat(self.date_from) > date.fromisoformat(self.date_to):
            raise ValueError("date_from must be before or equal to date_to")
        return self


@router.post("/run", status_code=202)
def run_crawl(body: CrawlRunIn, background_tasks: BackgroundTasks) -> dict:
    jobs = create_jobs(body.journal_ids, body.period, body.date_from, body.date_to)
    for job in jobs:
        background_tasks.add_task(run_crawl_job, job["job_id"], job["journal_id"], job["date_from"], job["date_to"])
    if not jobs:
        raise AppError(404, "no_active_journals", "No active journals matched crawl request")
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
        ]
    }


@router.get("/jobs")
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


@router.get("/jobs/{job_id}")
def get_job(job_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM crawl_jobs WHERE id=?", (job_id,)).fetchone()
        journal_row = None
        if row and row["journal_id"] is not None:
            journal_row = conn.execute("SELECT * FROM journals WHERE id=?", (row["journal_id"],)).fetchone()
    if not row:
        raise AppError(404, "crawl_job_not_found", "Crawl job not found")
    return serialize_job_detail(dict_from_row(row), dict_from_row(journal_row) if journal_row else None)
