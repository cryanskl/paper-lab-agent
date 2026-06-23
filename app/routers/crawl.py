from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel

from app.db import dict_from_row, get_conn
from app.errors import AppError, page
from app.services.crawl import create_jobs, run_crawl_job

router = APIRouter(prefix="/crawl", tags=["crawl"])


class CrawlRunIn(BaseModel):
    journal_ids: Optional[list[int]] = None
    period: str = "manual"
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@router.post("/run", status_code=202)
def run_crawl(body: CrawlRunIn, background_tasks: BackgroundTasks) -> dict:
    jobs = create_jobs(body.journal_ids, body.period, body.date_from, body.date_to)
    for job in jobs:
        background_tasks.add_task(run_crawl_job, job["job_id"], job["journal_id"], job["date_from"], job["date_to"])
    if not jobs:
        raise AppError(404, "no_active_journals", "No active journals matched crawl request")
    return {"jobs": [{"job_id": job["job_id"], "status": "pending"} for job in jobs]}


@router.get("/jobs")
def list_jobs(page_num: int = Query(1, alias="page", ge=1), page_size: int = Query(20, ge=1, le=100)) -> dict:
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM crawl_jobs").fetchone()["n"]
        rows = conn.execute("SELECT * FROM crawl_jobs ORDER BY id DESC LIMIT ? OFFSET ?", (page_size, offset)).fetchall()
    return page([dict_from_row(row) for row in rows], total, page_num, page_size)


@router.get("/jobs/{job_id}")
def get_job(job_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM crawl_jobs WHERE id=?", (job_id,)).fetchone()
    if not row:
        raise AppError(404, "crawl_job_not_found", "Crawl job not found")
    return dict_from_row(row)

