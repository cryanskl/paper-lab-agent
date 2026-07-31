import sqlite3
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field, field_validator, model_validator

from app.db import dict_from_row, get_conn
from app.errors import AppError, page


router = APIRouter(prefix="/glossary-terms", tags=["glossary"])


class GlossaryTermIn(BaseModel):
    en: Optional[str] = Field(default=None, max_length=120)
    zh: Optional[str] = Field(default=None, max_length=120)
    translation_job_id: Optional[int] = Field(default=None, ge=1)
    translation_status: Optional[str] = None
    translation_error: Optional[str] = Field(default=None, max_length=240)

    @field_validator("en", "zh", "translation_error")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        normalized = " ".join((value or "").split())
        return normalized or None

    @field_validator("translation_status")
    @classmethod
    def validate_translation_status(cls, value: Optional[str]) -> Optional[str]:
        normalized = (value or "").strip() or None
        if normalized not in {None, "pending", "failed"}:
            raise ValueError("translation_status must be pending, failed, or null")
        return normalized

    @model_validator(mode="after")
    def at_least_one_language(self) -> "GlossaryTermIn":
        if not self.en and not self.zh:
            raise ValueError("en and zh must not both be blank")
        return self


class GlossaryTermResponse(BaseModel):
    id: int
    en: str
    zh: str
    translation_job_id: Optional[int] = None
    translation_status: Optional[str] = None
    translation_error: str
    created_at: str
    updated_at: str


class GlossaryTermListResponse(BaseModel):
    items: list[GlossaryTermResponse]
    total: int
    page: int
    page_size: int


class GlossaryTermImportIn(BaseModel):
    items: list[GlossaryTermIn] = Field(max_length=500)


class GlossaryTermDeleteResponse(BaseModel):
    id: int
    en: str
    zh: str


def response_row(row: sqlite3.Row) -> dict:
    item = dict_from_row(row)
    item["en"] = item["en"] or ""
    item["zh"] = item["zh"] or ""
    item["translation_error"] = item["translation_error"] or ""
    return item


def find_conflict(
    conn: sqlite3.Connection,
    en: Optional[str],
    zh: Optional[str],
    *,
    excluded_id: Optional[int] = None,
) -> Optional[sqlite3.Row]:
    clauses: list[str] = []
    params: list[object] = []
    if en:
        clauses.append("en = ? COLLATE NOCASE")
        params.append(en)
    elif zh:
        clauses.append("zh = ? COLLATE NOCASE")
        params.append(zh)
    if not clauses:
        return None
    sql = f"SELECT * FROM glossary_terms WHERE ({' OR '.join(clauses)})"
    if excluded_id is not None:
        sql += " AND id != ?"
        params.append(excluded_id)
    sql += " ORDER BY id LIMIT 1"
    return conn.execute(sql, params).fetchone()


def conflict_error(row: sqlite3.Row) -> AppError:
    label = row["en"] or row["zh"]
    return AppError(409, "glossary_term_conflict", f'Glossary term "{label}" already exists')


@router.get("", response_model=GlossaryTermListResponse)
def list_glossary_terms(
    page_num: int = Query(1, alias="page", ge=1),
    page_size: int = Query(100, ge=1, le=500),
) -> dict:
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM glossary_terms").fetchone()["n"]
        rows = conn.execute(
            "SELECT * FROM glossary_terms ORDER BY id DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()
    return page([response_row(row) for row in rows], total, page_num, page_size)


@router.post("/import", response_model=GlossaryTermListResponse)
def import_glossary_terms(body: GlossaryTermImportIn) -> dict:
    with get_conn() as conn:
        for item in body.items:
            exact = None
            if item.en:
                exact = conn.execute(
                    "SELECT * FROM glossary_terms WHERE en = ? COLLATE NOCASE ORDER BY id LIMIT 1",
                    (item.en,),
                ).fetchone()
            elif item.zh:
                exact = conn.execute(
                    "SELECT * FROM glossary_terms WHERE zh = ? COLLATE NOCASE ORDER BY id LIMIT 1",
                    (item.zh,),
                ).fetchone()
            if exact is None:
                conn.execute(
                    """
                    INSERT INTO glossary_terms
                        (en, zh, translation_job_id, translation_status, translation_error)
                    VALUES (?, ?, NULL, ?, ?)
                    """,
                    (item.en, item.zh, item.translation_status, item.translation_error),
                )
                continue
            conn.execute(
                """
                UPDATE glossary_terms
                SET en=?, zh=?, translation_status=?, translation_error=?, updated_at=datetime('now')
                WHERE id=?
                """,
                (
                    exact["en"] or item.en,
                    exact["zh"] or item.zh,
                    item.translation_status or exact["translation_status"],
                    item.translation_error or exact["translation_error"],
                    exact["id"],
                ),
            )
        rows = conn.execute("SELECT * FROM glossary_terms ORDER BY id DESC").fetchall()
    return page([response_row(row) for row in rows], len(rows), 1, max(len(rows), 1))


@router.post("", status_code=201, response_model=GlossaryTermResponse)
def create_glossary_term(body: GlossaryTermIn) -> dict:
    with get_conn() as conn:
        conflict = find_conflict(conn, body.en, body.zh)
        if conflict is not None:
            raise conflict_error(conflict)
        cursor = conn.execute(
            """
            INSERT INTO glossary_terms
                (en, zh, translation_job_id, translation_status, translation_error)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                body.en,
                body.zh,
                body.translation_job_id,
                body.translation_status,
                body.translation_error,
            ),
        )
        row = conn.execute("SELECT * FROM glossary_terms WHERE id=?", (cursor.lastrowid,)).fetchone()
    return response_row(row)


@router.put("/{term_id}", response_model=GlossaryTermResponse)
def update_glossary_term(term_id: int, body: GlossaryTermIn) -> dict:
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM glossary_terms WHERE id=?", (term_id,)).fetchone()
        if existing is None:
            raise AppError(404, "glossary_term_not_found", "Glossary term not found")
        conflict = find_conflict(conn, body.en, body.zh, excluded_id=term_id)
        if conflict is not None:
            raise conflict_error(conflict)
        conn.execute(
            """
            UPDATE glossary_terms
            SET en=?, zh=?, translation_job_id=?, translation_status=?,
                translation_error=?, updated_at=datetime('now')
            WHERE id=?
            """,
            (
                body.en,
                body.zh,
                body.translation_job_id,
                body.translation_status,
                body.translation_error,
                term_id,
            ),
        )
        row = conn.execute("SELECT * FROM glossary_terms WHERE id=?", (term_id,)).fetchone()
    return response_row(row)


@router.delete("/{term_id}", response_model=GlossaryTermDeleteResponse)
def delete_glossary_term(term_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT id, en, zh FROM glossary_terms WHERE id=?", (term_id,)).fetchone()
        if row is None:
            raise AppError(404, "glossary_term_not_found", "Glossary term not found")
        conn.execute("DELETE FROM glossary_terms WHERE id=?", (term_id,))
    item = dict_from_row(row)
    item["en"] = item["en"] or ""
    item["zh"] = item["zh"] or ""
    return item
