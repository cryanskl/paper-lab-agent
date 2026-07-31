from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db import dict_from_row, get_conn

router = APIRouter(prefix="/paper-downloads", tags=["downloads"])


class DownloadPaperSummaryResponse(BaseModel):
    id: int
    doi: Optional[str] = None
    title: str
    journal_name: Optional[str] = None
    published_date: Optional[str] = None


class PaperDownloadItemResponse(BaseModel):
    id: int
    paper_id: int
    document_id: Optional[int] = None
    status: str
    error: Optional[str] = None
    created_at: str
    updated_at: str
    paper: DownloadPaperSummaryResponse


class PaperDownloadListResponse(BaseModel):
    items: list[PaperDownloadItemResponse]
    total: int
    page: int
    page_size: int
    status_counts: dict[str, int]


@router.get("", response_model=PaperDownloadListResponse)
def list_paper_downloads(
    status: Optional[str] = Query(
        None,
        pattern="^(pending|downloading|downloaded|failed)$",
    ),
    page_num: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    clauses = []
    params: list[object] = []
    if status is not None:
        clauses.append("pd.status=?")
        params.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM paper_downloads pd {where}",
            params,
        ).fetchone()["n"]
        rows = conn.execute(
            f"""
            SELECT
                pd.id, pd.paper_id, pd.document_id, pd.status, pd.error,
                pd.created_at, pd.updated_at,
                p.doi, p.title, p.journal_name, p.published_date
            FROM paper_downloads pd
            JOIN papers p ON p.id=pd.paper_id
            {where}
            ORDER BY pd.updated_at DESC, pd.id DESC
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset],
        ).fetchall()
        count_rows = conn.execute(
            """
            SELECT status, COUNT(*) AS n
            FROM paper_downloads
            GROUP BY status
            """
        ).fetchall()
    counts = {
        "pending": 0,
        "downloading": 0,
        "downloaded": 0,
        "failed": 0,
    }
    counts.update({row["status"]: row["n"] for row in count_rows})
    items = []
    for row in rows:
        item = dict_from_row(row)
        item["paper"] = {
            "id": item["paper_id"],
            "doi": item.pop("doi"),
            "title": item.pop("title"),
            "journal_name": item.pop("journal_name"),
            "published_date": item.pop("published_date"),
        }
        items.append(item)
    return {
        "items": items,
        "total": total,
        "page": page_num,
        "page_size": page_size,
        "status_counts": counts,
    }
