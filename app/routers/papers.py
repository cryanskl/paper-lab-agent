import re
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, field_validator

from app.clients.unpaywall import UnpaywallClient
from app.config import get_settings
from app.db import dict_from_row, get_conn
from app.errors import AppError, page
from app.services.crawl import unpaywall_client_options
from app.utils import json_loads

router = APIRouter(prefix="/papers", tags=["papers"])

FTS_SAFE_QUERY_RE = re.compile(r"^[\w\s]+$")


class CategoryOverrideIn(BaseModel):
    category_ids: list[int]
    method: str = "manual"

    @field_validator("method")
    @classmethod
    def method_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("method must not be blank")
        return normalized


def categories_for(conn, paper_id: int) -> list[str]:
    rows = conn.execute(
        """
        SELECT c.slug FROM paper_categories pc
        JOIN categories c ON c.id = pc.category_id
        WHERE pc.paper_id=?
        ORDER BY c.slug
        """,
        (paper_id,),
    ).fetchall()
    return [row["slug"] for row in rows]


def fts_query(value: str) -> str:
    if FTS_SAFE_QUERY_RE.fullmatch(value):
        return value
    return f'"{value.replace(chr(34), chr(34) + chr(34))}"'


def serialize_paper(row: dict, categories: list[str]) -> dict:
    return {
        "id": row["id"],
        "doi": row["doi"],
        "title": row["title"],
        "abstract": row["abstract"],
        "authors": json_loads(row.get("authors"), []),
        "journal_id": row["journal_id"],
        "journal_name": row["journal_name"],
        "published_date": row["published_date"],
        "published_year": row["published_year"],
        "oa_status": row["oa_status"],
        "oa_pdf_url": row["oa_pdf_url"],
        "landing_url": row["landing_url"],
        "source_api": row.get("source_api"),
        "dedupe_key": row.get("dedupe_key"),
        "has_doi": bool(row.get("doi")),
        "categories": categories,
    }


@router.get("")
def list_papers(
    q: Optional[str] = None,
    category: Optional[str] = None,
    journal_id: Optional[int] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    oa_only: bool = False,
    sort: str = Query("date_desc", pattern="^(date_desc|relevance)$"),
    page_num: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    q = q.strip() if q and q.strip() else None
    category = category.strip() if category and category.strip() else None
    if year_from is not None and year_to is not None and year_from > year_to:
        raise AppError(422, "validation_error", "year_from must be less than or equal to year_to")
    params = []
    joins = []
    clauses = []
    select_prefix = "SELECT DISTINCT p.* FROM papers p"
    count_prefix = "SELECT COUNT(DISTINCT p.id) AS n FROM papers p"
    if q:
        joins.append("JOIN papers_fts fts ON fts.rowid = p.id")
        clauses.append("papers_fts MATCH ?")
        params.append(fts_query(q))
    if category:
        joins.append("JOIN paper_categories pc ON pc.paper_id = p.id JOIN categories c ON c.id = pc.category_id")
        clauses.append("c.slug = ?")
        params.append(category)
    if journal_id is not None:
        clauses.append("p.journal_id = ?")
        params.append(journal_id)
    if year_from is not None:
        clauses.append("p.published_year >= ?")
        params.append(year_from)
    if year_to is not None:
        clauses.append("p.published_year <= ?")
        params.append(year_to)
    if oa_only:
        clauses.append("p.oa_pdf_url IS NOT NULL AND p.oa_pdf_url != ''")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    join_sql = " ".join(joins)
    order = "ORDER BY p.published_date DESC, p.id DESC"
    if sort == "relevance" and q:
        order = "ORDER BY bm25(papers_fts)"
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        total = conn.execute(f"{count_prefix} {join_sql} {where}", params).fetchone()["n"]
        rows = conn.execute(
            f"{select_prefix} {join_sql} {where} {order} LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
        items = []
        for row in rows:
            paper = dict_from_row(row)
            items.append(serialize_paper(paper, categories_for(conn, paper["id"])))
    return page(items, total, page_num, page_size)


@router.get("/{paper_id}")
def get_paper(paper_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM papers WHERE id=?", (paper_id,)).fetchone()
        if not row:
            raise AppError(404, "paper_not_found", "Paper not found")
        paper = dict_from_row(row)
        return serialize_paper(paper, categories_for(conn, paper_id)) | {"raw_metadata": json_loads(paper.get("raw_metadata"), {})}


@router.post("/{paper_id}/resolve-oa")
async def resolve_oa(paper_id: int) -> dict:
    settings = get_settings()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM papers WHERE id=?", (paper_id,)).fetchone()
    if not row:
        raise AppError(404, "paper_not_found", "Paper not found")
    paper = dict_from_row(row)
    if not paper.get("doi"):
        raise AppError(422, "paper_missing_doi", "Paper has no DOI")
    result = await UnpaywallClient(settings.unpaywall_email, **unpaywall_client_options(settings)).resolve(paper["doi"])
    with get_conn() as conn:
        conn.execute(
            "UPDATE papers SET oa_status=?, oa_pdf_url=?, updated_at=datetime('now') WHERE id=?",
            (result.get("oa_status") or "unknown", result.get("oa_pdf_url"), paper_id),
        )
    return get_paper(paper_id)


@router.post("/{paper_id}/classify")
def classify_paper(paper_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM papers WHERE id=?", (paper_id,)).fetchone()
        if not row:
            raise AppError(404, "paper_not_found", "Paper not found")
        text = f"{row['title']} {row['abstract'] or ''}".lower()
        categories = conn.execute("SELECT * FROM categories").fetchall()
        matched_ids = []
        for category_row in categories:
            slug = category_row["slug"]
            if slug in text or (category_row["name"] and category_row["name"].lower() in text):
                matched_ids.append(category_row["id"])
        if not matched_ids:
            method_id = conn.execute("SELECT id FROM categories WHERE slug='methods'").fetchone()
            if method_id:
                matched_ids.append(method_id["id"])
        conn.execute("DELETE FROM paper_categories WHERE paper_id=? AND method='auto'", (paper_id,))
        for category_id in matched_ids:
            conn.execute(
                """
                INSERT OR REPLACE INTO paper_categories (paper_id, category_id, confidence, method)
                VALUES (?, ?, ?, 'auto')
                """,
                (paper_id, category_id, 0.5),
            )
    return get_paper(paper_id)


@router.put("/{paper_id}/categories")
def override_categories(paper_id: int, body: CategoryOverrideIn) -> dict:
    category_ids = list(dict.fromkeys(body.category_ids))
    with get_conn() as conn:
        exists = conn.execute("SELECT id FROM papers WHERE id=?", (paper_id,)).fetchone()
        if not exists:
            raise AppError(404, "paper_not_found", "Paper not found")
        conn.execute("DELETE FROM paper_categories WHERE paper_id=?", (paper_id,))
        for category_id in category_ids:
            category = conn.execute("SELECT id FROM categories WHERE id=?", (category_id,)).fetchone()
            if not category:
                raise AppError(422, "category_not_found", f"Category {category_id} not found")
            conn.execute(
                """
                INSERT INTO paper_categories (paper_id, category_id, confidence, method)
                VALUES (?, ?, ?, ?)
                """,
                (paper_id, category_id, 1.0, body.method),
            )
    return get_paper(paper_id)
