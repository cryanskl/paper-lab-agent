from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, UploadFile
from pydantic import BaseModel, field_validator

from app.db import dict_from_row, get_conn
from app.errors import AppError, page
from app.services.chemistry import extract_reactions, mark_chemistry_queued
from app.services.documents import mark_parse_queued, parse_document, save_upload
from app.services.rag import index_document, mark_index_queued
from app.services.translation import create_translation_job, translate_document

router = APIRouter(prefix="/documents", tags=["documents"])


class TranslateIn(BaseModel):
    target_lang: str = "zh"

    @field_validator("target_lang")
    @classmethod
    def target_lang_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("target_lang must not be blank")
        return normalized


async def ensure_pdf_upload(file: UploadFile) -> None:
    suffix = Path(file.filename or "").suffix.lower()
    header = await file.read(5)
    await file.seek(0)
    if (suffix == ".pdf" or file.content_type == "application/pdf") and header.startswith(b"%PDF-"):
        return
    raise AppError(415, "unsupported_document_type", "Only PDF uploads are supported")


def paper_summary_for(conn, paper_id: Optional[int]) -> Optional[dict]:
    if paper_id is None:
        return None
    row = conn.execute(
        """
        SELECT id, doi, title, journal_name, published_date
        FROM papers
        WHERE id=?
        """,
        (paper_id,),
    ).fetchone()
    return dict_from_row(row) if row else None


def serialize_document(row, conn) -> dict:
    document = dict_from_row(row)
    document["paper"] = paper_summary_for(conn, document.get("paper_id"))
    return document


def get_document_or_404(document_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if not row:
            raise AppError(404, "document_not_found", "Document not found")
        return serialize_document(row, conn)


@router.post("", status_code=201)
async def upload_document(file: UploadFile = File(...), paper_id: Optional[int] = Form(None)) -> dict:
    await ensure_pdf_upload(file)
    if paper_id is not None:
        with get_conn() as conn:
            paper = conn.execute("SELECT id FROM papers WHERE id=?", (paper_id,)).fetchone()
        if paper is None:
            raise AppError(404, "paper_not_found", "Paper not found")
    doc, created = await save_upload(file, paper_id)
    document = get_document_or_404(doc["id"])
    if not created:
        raise AppError(
            409,
            "document_duplicate",
            f"Document already exists with id {doc['id']}",
            {"document": document},
        )
    return document


@router.get("")
def list_documents(
    page_num: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
        rows = conn.execute("SELECT * FROM documents ORDER BY id DESC LIMIT ? OFFSET ?", (page_size, offset)).fetchall()
        items = [serialize_document(row, conn) for row in rows]
    return page(items, total, page_num, page_size)


@router.get("/{document_id}")
def get_document(document_id: int) -> dict:
    return get_document_or_404(document_id)


@router.post("/{document_id}/parse", status_code=202)
def parse(document_id: int, background_tasks: BackgroundTasks) -> dict:
    get_document_or_404(document_id)
    mark_parse_queued(document_id)
    background_tasks.add_task(parse_document, document_id)
    return {"job_id": document_id, "document_id": document_id, "parse_status": "parsing", "status": "pending"}


@router.get("/{document_id}/sections")
def list_sections(
    document_id: int,
    page_num: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    get_document_or_404(document_id)
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM sections WHERE document_id=?", (document_id,)).fetchone()["n"]
        rows = conn.execute(
            "SELECT * FROM sections WHERE document_id=? ORDER BY seq LIMIT ? OFFSET ?",
            (document_id, page_size, offset),
        ).fetchall()
    return page([dict_from_row(row) for row in rows], total, page_num, page_size)


@router.get("/{document_id}/chunks")
def list_chunks(
    document_id: int,
    page_num: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    document = get_document_or_404(document_id)
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM chunks WHERE document_id=?", (document_id,)).fetchone()["n"]
        rows = conn.execute(
            """
            SELECT ch.*, s.title AS section_title
            FROM chunks ch
            LEFT JOIN sections s ON s.id = ch.section_id
            WHERE ch.document_id=?
            ORDER BY ch.seq
            LIMIT ? OFFSET ?
            """,
            (document_id, page_size, offset),
        ).fetchall()
    items = [dict_from_row(row) for row in rows]
    return {
        "items": items,
        "total": total,
        "page": page_num,
        "page_size": page_size,
        "indexed": document.get("index_status") == "indexed" and bool(items),
        "index_status": document.get("index_status") or ("indexed" if items else "not_indexed"),
        "index_error": document.get("index_error"),
    }


@router.post("/{document_id}/translate", status_code=202)
def translate(document_id: int, body: TranslateIn, background_tasks: BackgroundTasks) -> dict:
    get_document_or_404(document_id)
    translation = create_translation_job(document_id, body.target_lang)
    background_tasks.add_task(translate_document, document_id, body.target_lang, translation["id"])
    return {
        "job_id": translation["id"],
        "document_id": document_id,
        "target_lang": body.target_lang,
        "status": "pending",
    }


@router.get("/{document_id}/translation")
def get_translation(document_id: int) -> dict:
    get_document_or_404(document_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM translations WHERE document_id=? ORDER BY id DESC LIMIT 1",
            (document_id,),
        ).fetchone()
    if not row:
        raise AppError(404, "translation_not_found", "Translation not found")
    return dict_from_row(row)


@router.post("/{document_id}/index", status_code=202)
def index(document_id: int, background_tasks: BackgroundTasks) -> dict:
    get_document_or_404(document_id)
    mark_index_queued(document_id)
    background_tasks.add_task(index_document, document_id)
    return {"job_id": document_id, "document_id": document_id, "index_status": "indexing", "status": "pending"}


@router.post("/{document_id}/extract-chemistry", status_code=202)
def extract_chemistry(document_id: int, background_tasks: BackgroundTasks) -> dict:
    get_document_or_404(document_id)
    mark_chemistry_queued(document_id)
    background_tasks.add_task(extract_reactions, document_id)
    return {"job_id": document_id, "document_id": document_id, "chemistry_status": "extracting", "status": "pending"}


@router.get("/{document_id}/reaction-sets")
def document_reaction_sets(
    document_id: int,
    page_num: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    get_document_or_404(document_id)
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM reaction_sets WHERE document_id=?", (document_id,)).fetchone()["n"]
        rows = conn.execute(
            "SELECT * FROM reaction_sets WHERE document_id=? ORDER BY id LIMIT ? OFFSET ?",
            (document_id, page_size, offset),
        ).fetchall()
    return page([dict_from_row(row) for row in rows], total, page_num, page_size)
