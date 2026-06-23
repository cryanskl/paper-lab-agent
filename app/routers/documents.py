from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from pydantic import BaseModel

from app.db import dict_from_row, get_conn
from app.errors import AppError, page
from app.services.chemistry import extract_reactions
from app.services.documents import parse_document, save_upload
from app.services.rag import index_document
from app.services.translation import translate_document

router = APIRouter(prefix="/documents", tags=["documents"])


class TranslateIn(BaseModel):
    target_lang: str = "zh"


def get_document_or_404(document_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
    if not row:
        raise AppError(404, "document_not_found", "Document not found")
    return dict_from_row(row)


@router.post("", status_code=201)
async def upload_document(file: UploadFile = File(...), paper_id: Optional[int] = Form(None)) -> dict:
    doc, created = await save_upload(file, paper_id)
    if not created:
        raise AppError(409, "document_duplicate", f"Document already exists with id {doc['id']}")
    return doc


@router.get("")
def list_documents(page_num: int = 1, page_size: int = 20) -> dict:
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
        rows = conn.execute("SELECT * FROM documents ORDER BY id DESC LIMIT ? OFFSET ?", (page_size, offset)).fetchall()
    return page([dict_from_row(row) for row in rows], total, page_num, page_size)


@router.get("/{document_id}")
def get_document(document_id: int) -> dict:
    return get_document_or_404(document_id)


@router.post("/{document_id}/parse", status_code=202)
def parse(document_id: int, background_tasks: BackgroundTasks) -> dict:
    get_document_or_404(document_id)
    background_tasks.add_task(parse_document, document_id)
    return {"job_id": document_id, "status": "pending"}


@router.get("/{document_id}/sections")
def list_sections(document_id: int) -> dict:
    get_document_or_404(document_id)
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM sections WHERE document_id=? ORDER BY seq", (document_id,)).fetchall()
    return {"items": [dict_from_row(row) for row in rows]}


@router.post("/{document_id}/translate", status_code=202)
def translate(document_id: int, body: TranslateIn, background_tasks: BackgroundTasks) -> dict:
    get_document_or_404(document_id)
    background_tasks.add_task(translate_document, document_id, body.target_lang)
    return {"job_id": document_id, "status": "pending"}


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
    background_tasks.add_task(index_document, document_id)
    return {"job_id": document_id, "status": "pending"}


@router.post("/{document_id}/extract-chemistry", status_code=202)
def extract_chemistry(document_id: int, background_tasks: BackgroundTasks) -> dict:
    get_document_or_404(document_id)
    background_tasks.add_task(extract_reactions, document_id)
    return {"job_id": document_id, "status": "pending"}


@router.get("/{document_id}/reaction-sets")
def document_reaction_sets(document_id: int) -> dict:
    get_document_or_404(document_id)
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM reaction_sets WHERE document_id=? ORDER BY id", (document_id,)).fetchall()
    return {"items": [dict_from_row(row) for row in rows]}

