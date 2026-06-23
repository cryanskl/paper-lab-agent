from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db import dict_from_row, get_conn
from app.errors import AppError, page
from app.utils import json_dumps, json_loads, to_int

router = APIRouter(prefix="/journals", tags=["journals"])


class JournalIn(BaseModel):
    name: str
    publisher: Optional[str] = None
    platform: Optional[str] = None
    url: Optional[str] = None
    issn_print: Optional[str] = None
    issn_electronic: Optional[str] = None
    keywords: list[str] = []
    year_from: int = 1990
    year_to: Optional[int] = None
    sci_zone: Optional[str] = None
    impact_factor: Optional[float] = None
    active: bool = True


class JournalUpdate(BaseModel):
    name: Optional[str] = None
    publisher: Optional[str] = None
    platform: Optional[str] = None
    url: Optional[str] = None
    issn_print: Optional[str] = None
    issn_electronic: Optional[str] = None
    keywords: Optional[list[str]] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    sci_zone: Optional[str] = None
    impact_factor: Optional[float] = None
    active: Optional[bool] = None


def serialize(row: dict) -> dict:
    row["keywords"] = json_loads(row.get("keywords"), [])
    row["active"] = bool(row.get("active"))
    return row


@router.get("")
def list_journals(
    active: Optional[bool] = None,
    page_num: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    clauses = []
    params = []
    active_int = to_int(active)
    if active_int is not None:
        clauses.append("active=?")
        params.append(active_int)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS n FROM journals {where}", params).fetchone()["n"]
        rows = conn.execute(
            f"SELECT * FROM journals {where} ORDER BY id LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
    return page([serialize(dict_from_row(row)) for row in rows], total, page_num, page_size)


@router.post("", status_code=201)
def create_journal(body: JournalIn) -> dict:
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO journals (
                name, publisher, platform, url, issn_print, issn_electronic, keywords,
                year_from, year_to, sci_zone, impact_factor, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.name,
                body.publisher,
                body.platform,
                body.url,
                body.issn_print,
                body.issn_electronic,
                json_dumps(body.keywords),
                body.year_from,
                body.year_to,
                body.sci_zone,
                body.impact_factor,
                1 if body.active else 0,
            ),
        )
        row = conn.execute("SELECT * FROM journals WHERE id=?", (cursor.lastrowid,)).fetchone()
    return serialize(dict_from_row(row))


@router.get("/{journal_id}")
def get_journal(journal_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM journals WHERE id=?", (journal_id,)).fetchone()
    if not row:
        raise AppError(404, "journal_not_found", "Journal not found")
    return serialize(dict_from_row(row))


@router.put("/{journal_id}")
def update_journal(journal_id: int, body: JournalUpdate) -> dict:
    data = body.model_dump(exclude_unset=True)
    if "keywords" in data:
        data["keywords"] = json_dumps(data["keywords"])
    if "active" in data:
        data["active"] = 1 if data["active"] else 0
    if data:
        assignments = ", ".join(f"{key}=?" for key in data.keys())
        with get_conn() as conn:
            conn.execute(f"UPDATE journals SET {assignments}, updated_at=datetime('now') WHERE id=?", list(data.values()) + [journal_id])
    return get_journal(journal_id)


@router.delete("/{journal_id}")
def delete_journal(journal_id: int) -> dict:
    with get_conn() as conn:
        result = conn.execute("UPDATE journals SET active=0, updated_at=datetime('now') WHERE id=?", (journal_id,))
        if result.rowcount == 0:
            raise AppError(404, "journal_not_found", "Journal not found")
    return get_journal(journal_id)

