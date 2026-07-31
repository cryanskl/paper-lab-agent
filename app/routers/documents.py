import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, field_validator

from app.config import get_settings
from app.db import dict_from_row, get_conn
from app.errors import AppError, AsyncJobResponse, PageResponse, page
from app.services.chemistry import (
    ConfirmedReactionSetExistsError,
    extract_reactions,
    mark_chemistry_queued,
)
from app.services.document_pipeline import run_document_pipeline
from app.services.documents import (
    assert_safe_document_storage_path,
    figures_from_tei,
    mark_parse_queued,
    normalize_reader_text,
    parse_document,
    render_figure_png,
    save_upload,
)
from app.services.rag import index_document, mark_index_queued
from app.services.translation import create_translation_job, translate_document, translation_sections

router = APIRouter(prefix="/documents", tags=["documents"])


def normalize_target_lang(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("target_lang must not be blank")
    if any(char in normalized for char in ("/", "\\")):
        raise ValueError("target_lang must not contain path separators")
    if any(ord(char) < 32 for char in normalized):
        raise ValueError("target_lang must not contain control characters")
    return normalized


class TranslateIn(BaseModel):
    target_lang: str = "zh"

    @field_validator("target_lang")
    @classmethod
    def target_lang_must_not_be_blank(cls, value: str) -> str:
        return normalize_target_lang(value)


class PaperSummaryResponse(BaseModel):
    id: int
    doi: Optional[str] = None
    title: Optional[str] = None
    journal_name: Optional[str] = None
    published_date: Optional[str] = None


class DocumentResponse(BaseModel):
    id: int
    paper_id: Optional[int] = None
    file_path: str
    file_hash: Optional[str] = None
    original_name: Optional[str] = None
    num_pages: Optional[int] = None
    parse_status: str
    parse_error: Optional[str] = None
    index_status: str
    index_error: Optional[str] = None
    chemistry_status: str
    chemistry_error: Optional[str] = None
    tei_path: Optional[str] = None
    created_at: str
    paper: Optional[PaperSummaryResponse] = None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class TranslationSectionResponse(BaseModel):
    section_id: Optional[int] = None
    seq: Optional[int] = None
    title: Optional[str] = None
    section_type: Optional[str] = None
    source: str
    target: str
    note: Optional[str] = None


class TranslationResponse(BaseModel):
    id: int
    document_id: int
    source_lang: Optional[str] = None
    target_lang: str
    status: str
    output_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    sections: list[TranslationSectionResponse] = []


class SectionResponse(BaseModel):
    id: int
    document_id: int
    parent_id: Optional[int] = None
    seq: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    section_type: Optional[str] = None


class SectionListResponse(BaseModel):
    items: list[SectionResponse]
    total: int
    page: int
    page_size: int


class FigureResponse(BaseModel):
    id: str
    label: str
    title: str
    caption: str
    page: int
    x: float
    y: float
    width: float
    height: float
    image_url: str


class FigureListResponse(BaseModel):
    items: list[FigureResponse]
    total: int
    page: int
    page_size: int


class ChunkResponse(BaseModel):
    id: int
    document_id: int
    section_id: Optional[int] = None
    seq: Optional[int] = None
    text: str
    token_count: Optional[int] = None
    vector_id: Optional[str] = None
    embedded: bool
    created_at: str
    section_title: Optional[str] = None


class ChunkListResponse(BaseModel):
    items: list[ChunkResponse]
    total: int
    page: int
    page_size: int
    indexed: bool
    index_status: str
    index_error: Optional[str] = None


class ReactionSetListItemResponse(BaseModel):
    id: int
    document_id: Optional[int] = None
    name: Optional[str] = None
    gas_mixture: Optional[str] = None
    lxcat_db: Optional[str] = None
    source_note: Optional[str] = None
    status: str
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    created_at: str
    reaction_count: int
    verified_count: int
    unverified_count: int
    accepted_count: int
    rejected_count: int
    pending_count: int
    export_ready: bool


class ReactionSetListResponse(BaseModel):
    items: list[ReactionSetListItemResponse]
    total: int
    page: int
    page_size: int


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


def resolve_document_pdf_path(document: dict) -> Path:
    configured_root = get_settings().pdf_dir.resolve()
    raw_path = Path(document["file_path"])
    try:
        assert_safe_document_storage_path(raw_path)
        path = raw_path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AppError(409, "document_file_unavailable", str(exc)) from exc
    if path != configured_root and configured_root not in path.parents:
        raise AppError(
            409,
            "document_file_outside_storage",
            "Document file is outside the configured PDF directory",
        )
    if not path.is_file():
        raise AppError(409, "document_file_unavailable", "Document PDF file is unavailable")
    try:
        with path.open("rb") as file_handle:
            signature = file_handle.read(5)
    except OSError as exc:
        raise AppError(409, "document_file_unavailable", str(exc)) from exc
    if signature != b"%PDF-":
        raise AppError(415, "document_file_not_pdf", "Document file is not a PDF")
    return path


def document_figures(document: dict) -> list[dict]:
    raw_tei_path = document.get("tei_path")
    if not raw_tei_path:
        raise AppError(409, "document_tei_unavailable", "Document TEI file is unavailable")
    configured_root = get_settings().tei_dir.resolve()
    raw_path = Path(raw_tei_path)
    try:
        assert_safe_document_storage_path(raw_path)
        path = raw_path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise AppError(409, "document_tei_unavailable", str(exc)) from exc
    if path != configured_root and configured_root not in path.parents:
        raise AppError(
            409,
            "document_tei_outside_storage",
            "Document TEI file is outside the configured TEI directory",
        )
    if not path.is_file():
        raise AppError(409, "document_tei_unavailable", "Document TEI file is unavailable")
    try:
        tei = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AppError(409, "document_tei_unavailable", str(exc)) from exc
    return figures_from_tei(tei, document["id"])


@router.post(
    "",
    status_code=201,
    response_model=DocumentResponse,
    responses={
        409: {"description": "Duplicate document"},
        415: {"description": "Unsupported document type"},
        500: {"description": "Document upload failed"},
    },
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    paper_id: Optional[int] = Form(None),
    auto_process: bool = Form(False),
    target_lang: str = Form("zh"),
) -> dict:
    await ensure_pdf_upload(file)
    try:
        target_lang = normalize_target_lang(target_lang)
    except ValueError as exc:
        raise AppError(422, "validation_error", str(exc))
    if paper_id is not None:
        with get_conn() as conn:
            paper = conn.execute("SELECT id FROM papers WHERE id=?", (paper_id,)).fetchone()
        if paper is None:
            raise AppError(404, "paper_not_found", "Paper not found")
    try:
        doc, created = await save_upload(file, paper_id)
    except OSError as exc:
        raise AppError(500, "document_upload_failed", str(exc))
    document = get_document_or_404(doc["id"])
    if not created:
        raise AppError(
            409,
            "document_duplicate",
            f"Document already exists with id {doc['id']}",
            {"document": document},
        )
    if auto_process:
        try:
            mark_parse_queued(document["id"])
        except Exception as exc:
            raise AppError(500, "document_pipeline_queue_failed", str(exc))
        background_tasks.add_task(run_document_pipeline, document["id"], target_lang)
        document = get_document_or_404(document["id"])
    return document


@router.get("", response_model=DocumentListResponse)
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


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int) -> dict:
    return get_document_or_404(document_id)


@router.get(
    "/{document_id}/file",
    response_class=FileResponse,
    responses={
        200: {
            "description": "Locally stored PDF",
            "content": {
                "application/pdf": {
                    "schema": {"type": "string", "format": "binary"},
                }
            },
        }
    },
)
def open_document_file(document_id: int) -> Response:
    document = get_document_or_404(document_id)
    path = resolve_document_pdf_path(document)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=document.get("original_name") or f"document-{document_id}.pdf",
        content_disposition_type="inline",
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{document_id}/figures", response_model=FigureListResponse)
def list_figures(
    document_id: int,
    page_num: int = Query(1, alias="page", ge=1),
    page_size: int = Query(100, ge=1, le=100),
) -> dict:
    document = get_document_or_404(document_id)
    figures = document_figures(document)
    offset = (page_num - 1) * page_size
    return page(figures[offset : offset + page_size], len(figures), page_num, page_size)


@router.get(
    "/{document_id}/figures/{figure_id}/image",
    response_class=Response,
    responses={
        200: {
            "description": "Figure crop rendered from the locally stored PDF",
            "content": {
                "image/png": {
                    "schema": {"type": "string", "format": "binary"},
                }
            },
        }
    },
)
def open_figure_image(document_id: int, figure_id: str) -> Response:
    document = get_document_or_404(document_id)
    figure = next(
        (item for item in document_figures(document) if item["id"] == figure_id),
        None,
    )
    if figure is None:
        raise AppError(404, "document_figure_not_found", "Document figure not found")
    path = resolve_document_pdf_path(document)
    try:
        content = render_figure_png(path, figure)
    except (OSError, RuntimeError, ValueError) as exc:
        raise AppError(409, "document_figure_unavailable", str(exc)) from exc
    return Response(
        content=content,
        media_type="image/png",
        headers={
            "Cache-Control": "private, max-age=3600",
            "Content-Disposition": f'inline; filename="{figure_id}.png"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/{document_id}/parse", status_code=202, response_model=AsyncJobResponse, response_model_exclude_none=True)
def parse(document_id: int, background_tasks: BackgroundTasks) -> dict:
    get_document_or_404(document_id)
    try:
        mark_parse_queued(document_id)
    except ConfirmedReactionSetExistsError as exc:
        raise AppError(409, "confirmed_reaction_set_exists", str(exc))
    except Exception as exc:
        raise AppError(500, "parse_queue_failed", str(exc))
    background_tasks.add_task(parse_document, document_id)
    return {"job_id": document_id, "document_id": document_id, "parse_status": "parsing", "status": "pending"}


@router.get("/{document_id}/sections", response_model=SectionListResponse)
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
    items = [dict_from_row(row) for row in rows]
    for item in items:
        item["content"] = normalize_reader_text(item.get("content"))
    return page(items, total, page_num, page_size)


@router.get("/{document_id}/chunks", response_model=ChunkListResponse)
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
            ORDER BY s.seq, ch.seq, ch.id
            LIMIT ? OFFSET ?
            """,
            (document_id, page_size, offset),
        ).fetchall()
    items = [dict_from_row(row) for row in rows]
    indexed = document.get("index_status") == "indexed" and total > 0
    return {
        "items": items,
        "total": total,
        "page": page_num,
        "page_size": page_size,
        "indexed": indexed,
        "index_status": document.get("index_status") or ("indexed" if items else "not_indexed"),
        "index_error": document.get("index_error"),
    }


@router.post("/{document_id}/translate", status_code=202, response_model=AsyncJobResponse, response_model_exclude_none=True)
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


@router.get("/{document_id}/translation", response_model=TranslationResponse)
def get_translation(document_id: int) -> dict:
    get_document_or_404(document_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM translations WHERE document_id=? ORDER BY id DESC LIMIT 1",
            (document_id,),
        ).fetchone()
    if not row:
        raise AppError(404, "translation_not_found", "Translation not found")
    translation = dict_from_row(row)
    translation["sections"] = translation_sections(document_id, translation.get("output_path"))
    return translation


@router.post("/{document_id}/index", status_code=202, response_model=AsyncJobResponse, response_model_exclude_none=True)
def index(document_id: int, background_tasks: BackgroundTasks) -> dict:
    get_document_or_404(document_id)
    try:
        mark_index_queued(document_id)
    except Exception as exc:
        raise AppError(500, "index_queue_failed", str(exc))
    background_tasks.add_task(index_document, document_id)
    return {"job_id": document_id, "document_id": document_id, "index_status": "indexing", "status": "pending"}


@router.post(
    "/{document_id}/extract-chemistry",
    status_code=202,
    response_model=AsyncJobResponse,
    response_model_exclude_none=True,
)
def extract_chemistry(document_id: int, background_tasks: BackgroundTasks) -> dict:
    get_document_or_404(document_id)
    try:
        mark_chemistry_queued(document_id)
    except ConfirmedReactionSetExistsError as exc:
        raise AppError(409, "confirmed_reaction_set_exists", str(exc))
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc).lower():
            raise AppError(
                409,
                "document_busy",
                "Document is busy with another processing task; retry after it finishes",
            )
        raise AppError(500, "chemistry_queue_failed", str(exc))
    except Exception as exc:
        raise AppError(500, "chemistry_queue_failed", str(exc))
    background_tasks.add_task(extract_reactions, document_id)
    return {"job_id": document_id, "document_id": document_id, "chemistry_status": "extracting", "status": "pending"}


@router.get("/{document_id}/reaction-sets", response_model=ReactionSetListResponse)
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
            """
            SELECT
                reaction_sets.*,
                COUNT(reactions.id) AS reaction_count,
                COALESCE(SUM(CASE WHEN reactions.verified = 1 OR reactions.review_status = 'accepted' THEN 1 ELSE 0 END), 0) AS verified_count,
                COALESCE(SUM(CASE WHEN reactions.review_status = 'rejected' THEN 1 ELSE 0 END), 0) AS rejected_count,
                COALESCE(SUM(CASE WHEN reactions.verified = 0 AND reactions.review_status = 'pending' THEN 1 ELSE 0 END), 0) AS unverified_count
            FROM reaction_sets
            LEFT JOIN reactions ON reactions.reaction_set_id = reaction_sets.id
            WHERE reaction_sets.document_id=?
            GROUP BY reaction_sets.id
            ORDER BY reaction_sets.id
            LIMIT ? OFFSET ?
            """,
            (document_id, page_size, offset),
        ).fetchall()
    items = []
    for row in rows:
        item = dict_from_row(row)
        reaction_count = int(item.get("reaction_count") or 0)
        verified_count = int(item.get("verified_count") or 0)
        unverified_count = int(item.get("unverified_count") or 0)
        rejected_count = int(item.get("rejected_count") or 0)
        item["reaction_count"] = reaction_count
        item["verified_count"] = verified_count
        item["unverified_count"] = unverified_count
        item["accepted_count"] = verified_count
        item["rejected_count"] = rejected_count
        item["pending_count"] = unverified_count
        item["export_ready"] = verified_count > 0 and unverified_count == 0
        items.append(item)
    return page(items, total, page_num, page_size)
