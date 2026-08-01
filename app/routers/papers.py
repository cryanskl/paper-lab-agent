import re
from typing import Any, Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, BackgroundTasks, Query, Request
from pydantic import BaseModel, field_validator

from app.clients.unpaywall import UnpaywallClient, oa_status, web_url
from app.config import get_settings
from app.db import dict_from_row, get_conn
from app.errors import AppError, page
from app.services.classification import get_classifier
from app.services.crawl import normalize_doi, normalize_search_terms, unpaywall_client_options
from app.services.paper_downloads import (
    create_paper_download_job,
    download_paper_to_library,
    paper_download_state,
)
from app.services.translation import (
    TranslationUnavailableError,
    create_paper_abstract_translation_job,
    require_translation_capability,
    translate_paper_abstract,
)
from app.utils import json_dumps, json_loads

router = APIRouter(prefix="/papers", tags=["papers"])

FTS_SAFE_QUERY_RE = re.compile(r"^[\w\s]+$")


def normalize_target_lang(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("target_lang must not be blank")
    if any(char in normalized for char in ("/", "\\")):
        raise ValueError("target_lang must not contain path separators")
    if any(ord(char) < 32 for char in normalized):
        raise ValueError("target_lang must not contain control characters")
    return normalized


def is_downloadable_oa_url(value: Any) -> int:
    candidate = str(value or "").strip()
    if not candidate:
        return 0
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return 0
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme.lower() not in {"http", "https"} or not hostname:
        return 0
    if hostname == "example.test" or hostname.endswith(".example.test"):
        return 0
    return 1


def paper_pdf_filename(paper_id: int, title: Any) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", str(title or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    cleaned = cleaned[:120].rstrip(" .")
    return f"{cleaned or f'paper-{paper_id}'}.pdf"


class CategoryOverrideIn(BaseModel):
    category_ids: list[int]
    method: str = "manual"

    @field_validator("method")
    @classmethod
    def method_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("method must not be blank")
        if normalized != "manual":
            raise ValueError("method must be manual")
        return normalized


class CategoryDetailResponse(BaseModel):
    id: int
    slug: str
    name: str
    confidence: Optional[float] = None
    method: str


class PaperDownloadStateResponse(BaseModel):
    status: str
    error: Optional[str] = None
    document_id: Optional[int] = None
    downloaded_at: Optional[str] = None


class PaperDetailResponse(BaseModel):
    id: int
    doi: Optional[str] = None
    title: str
    abstract: Optional[str] = None
    authors: list[dict[str, Any]]
    journal_id: Optional[int] = None
    journal_name: Optional[str] = None
    published_date: Optional[str] = None
    published_year: Optional[int] = None
    oa_status: Optional[str] = None
    oa_pdf_url: Optional[str] = None
    landing_url: Optional[str] = None
    source_api: Optional[str] = None
    dedupe_key: Optional[str] = None
    has_doi: bool
    dedupe_strategy: str
    categories: list[str]
    category_details: list[CategoryDetailResponse]
    download: PaperDownloadStateResponse
    raw_metadata: dict[str, Any]


class PaperListItemResponse(BaseModel):
    id: int
    doi: Optional[str] = None
    title: str
    abstract: Optional[str] = None
    authors: list[dict[str, Any]]
    journal_id: Optional[int] = None
    journal_name: Optional[str] = None
    published_date: Optional[str] = None
    published_year: Optional[int] = None
    oa_status: Optional[str] = None
    oa_pdf_url: Optional[str] = None
    landing_url: Optional[str] = None
    source_api: Optional[str] = None
    dedupe_key: Optional[str] = None
    has_doi: bool
    dedupe_strategy: str
    categories: list[str]
    category_details: list[CategoryDetailResponse]
    download: PaperDownloadStateResponse


class PaperListResponse(BaseModel):
    items: list[PaperListItemResponse]
    total: int
    page: int
    page_size: int


class PaperDownloadJobResponse(BaseModel):
    job_id: int
    paper_id: int
    document_id: Optional[int] = None
    status: str
    error: Optional[str] = None


class AbstractTranslationIn(BaseModel):
    target_lang: str = "zh"

    @field_validator("target_lang")
    @classmethod
    def target_lang_must_be_safe(cls, value: str) -> str:
        return normalize_target_lang(value)


class AbstractTranslationJobResponse(BaseModel):
    job_id: int
    paper_id: int
    target_lang: str
    status: str


class AbstractTranslationResponse(BaseModel):
    id: int
    paper_id: int
    source_lang: Optional[str] = None
    target_lang: str
    source_text: str
    target_text: Optional[str] = None
    status: str
    error: Optional[str] = None
    created_at: str
    updated_at: str


def category_details_for(conn, paper_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT c.id, c.slug, c.name, pc.confidence, pc.method
        FROM paper_categories pc
        JOIN categories c ON c.id = pc.category_id
        WHERE pc.paper_id=?
        ORDER BY c.slug
        """,
        (paper_id,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "slug": row["slug"],
            "name": row["name"],
            "confidence": row["confidence"],
            "method": row["method"],
        }
        for row in rows
    ]


def fts_query(value: str) -> str:
    if FTS_SAFE_QUERY_RE.fullmatch(value):
        return value
    return f'"{value.replace(chr(34), chr(34) + chr(34))}"'


def boolean_fts_query(value: str, mode: str) -> str:
    terms = normalize_search_terms(value)
    if not terms:
        return fts_query(value)
    operator = " AND " if mode == "and" else " OR "
    operands = [f'"{term.replace(chr(34), chr(34) + chr(34))}"' for term in terms]
    return operator.join(operands)


def dedupe_strategy(row: dict) -> str:
    if row.get("doi"):
        return "doi"
    if str(row.get("dedupe_key") or "").startswith("no-doi:"):
        return "no_doi_fingerprint"
    return "none"


def serialize_paper(row: dict, category_details: list[dict], conn) -> dict:
    categories = [category["slug"] for category in category_details]
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
        "dedupe_strategy": dedupe_strategy(row),
        "categories": categories,
        "category_details": category_details,
        "download": paper_download_state(
            conn,
            row["id"],
            bool(is_downloadable_oa_url(row.get("oa_pdf_url"))),
        ),
    }


@router.get("", response_model=PaperListResponse)
def list_papers(
    q: Optional[str] = None,
    category: Optional[str] = None,
    journal_id: Optional[int] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    oa_only: bool = False,
    downloadable_only: bool = False,
    downloaded_only: bool = False,
    search_id: Optional[int] = Query(None, ge=1),
    sort: str = Query("date_desc", pattern="^(date_desc|relevance)$"),
    q_mode: Optional[str] = Query(None, pattern="^(and|or)$"),
    result_limit: Optional[int] = Query(None, ge=1, le=100),
    page_num: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    q = q.strip() if q and q.strip() else None
    category = category.strip() if category and category.strip() else None
    if sort == "relevance" and not q:
        raise AppError(422, "validation_error", "sort=relevance requires q")
    if year_from is not None and year_to is not None and year_from > year_to:
        raise AppError(422, "validation_error", "year_from must be less than or equal to year_to")
    params = []
    joins = []
    clauses = []
    select_prefix = "SELECT DISTINCT p.* FROM papers p"
    count_prefix = "SELECT COUNT(DISTINCT p.id) AS n FROM papers p"
    if search_id is not None:
        joins.append("JOIN search_results sr ON sr.paper_id = p.id")
        clauses.append("sr.search_history_id = ?")
        params.append(search_id)
    else:
        clauses.append("p.library_status = 'saved'")
    if q:
        joins.append("JOIN papers_fts fts ON fts.rowid = p.id")
        clauses.append("papers_fts MATCH ?")
        params.append(boolean_fts_query(q, q_mode) if q_mode else fts_query(q))
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
    if downloadable_only:
        clauses.append("is_downloadable_oa_url(p.oa_pdf_url) = 1")
    if downloaded_only:
        clauses.append("EXISTS (SELECT 1 FROM documents d WHERE d.paper_id = p.id)")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    join_sql = " ".join(joins)
    order = "ORDER BY p.published_date DESC, p.id DESC"
    if sort == "relevance" and q:
        order = "ORDER BY bm25(papers_fts)"
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        conn.create_function(
            "is_downloadable_oa_url",
            1,
            is_downloadable_oa_url,
            deterministic=True,
        )
        total = conn.execute(f"{count_prefix} {join_sql} {where}", params).fetchone()["n"]
        if result_limit is not None:
            total = min(total, result_limit)
        remaining = max(total - offset, 0)
        row_limit = min(page_size, remaining)
        rows = (
            conn.execute(
                f"{select_prefix} {join_sql} {where} {order} LIMIT ? OFFSET ?",
                params + [row_limit, offset],
            ).fetchall()
            if row_limit
            else []
        )
        items = []
        for row in rows:
            paper = dict_from_row(row)
            items.append(serialize_paper(paper, category_details_for(conn, paper["id"]), conn))
    return page(items, total, page_num, page_size)


@router.get("/{paper_id}", response_model=PaperDetailResponse)
def get_paper(paper_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM papers WHERE id=?", (paper_id,)).fetchone()
        if not row:
            raise AppError(404, "paper_not_found", "Paper not found")
        paper = dict_from_row(row)
        return serialize_paper(paper, category_details_for(conn, paper_id), conn) | {
            "raw_metadata": json_loads(paper.get("raw_metadata"), {})
        }


@router.post(
    "/{paper_id}/abstract-translation",
    status_code=202,
    response_model=AbstractTranslationJobResponse,
    responses={409: {"description": "Abstract missing or machine translation unavailable"}},
)
def start_abstract_translation(
    paper_id: int,
    body: AbstractTranslationIn,
    background_tasks: BackgroundTasks,
) -> dict:
    with get_conn() as conn:
        paper = conn.execute("SELECT id, abstract FROM papers WHERE id=?", (paper_id,)).fetchone()
    if paper is None:
        raise AppError(404, "paper_not_found", "Paper not found")
    if not str(paper["abstract"] or "").strip():
        raise AppError(409, "paper_abstract_missing", "Paper metadata has no abstract")
    try:
        require_translation_capability()
    except TranslationUnavailableError as exc:
        raise AppError(409, "translation_unavailable", str(exc)) from exc
    translation, cached = create_paper_abstract_translation_job(paper_id, body.target_lang)
    if not cached:
        background_tasks.add_task(
            translate_paper_abstract,
            paper_id,
            body.target_lang,
            translation["id"],
        )
    return {
        "job_id": translation["id"],
        "paper_id": paper_id,
        "target_lang": body.target_lang,
        "status": translation["status"],
    }


@router.get(
    "/{paper_id}/abstract-translation",
    response_model=AbstractTranslationResponse,
)
def get_abstract_translation(
    paper_id: int,
    target_lang: str = Query("zh", min_length=1),
) -> dict:
    try:
        normalized_target_lang = normalize_target_lang(target_lang)
    except ValueError as exc:
        raise AppError(422, "validation_error", str(exc)) from exc
    with get_conn() as conn:
        paper = conn.execute("SELECT id FROM papers WHERE id=?", (paper_id,)).fetchone()
        if paper is None:
            raise AppError(404, "paper_not_found", "Paper not found")
        row = conn.execute(
            """
            SELECT *
            FROM paper_abstract_translations
            WHERE paper_id=? AND target_lang=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (paper_id, normalized_target_lang),
        ).fetchone()
    if row is None:
        raise AppError(404, "abstract_translation_not_found", "Abstract translation not found")
    return dict_from_row(row)


@router.post(
    "/{paper_id}/download",
    status_code=202,
    response_model=PaperDownloadJobResponse,
    responses={
        409: {"description": "Open-access PDF unavailable"},
    },
)
def start_paper_pdf_download(
    paper_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    job = create_paper_download_job(paper_id)
    if job["should_start"]:
        background_tasks.add_task(
            download_paper_to_library,
            paper_id,
            request.headers.get("user-agent", ""),
        )
    return {
        "job_id": job["id"],
        "paper_id": paper_id,
        "document_id": job.get("document_id"),
        "status": "downloaded" if job["already_downloaded"] else "downloading",
        "error": job.get("error"),
    }


@router.post("/{paper_id}/resolve-oa", response_model=PaperDetailResponse)
async def resolve_oa(paper_id: int) -> dict:
    settings = get_settings()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM papers WHERE id=?", (paper_id,)).fetchone()
    if not row:
        raise AppError(404, "paper_not_found", "Paper not found")
    paper = dict_from_row(row)
    normalized_doi = normalize_doi(paper.get("doi"))
    if not normalized_doi:
        raise AppError(422, "paper_missing_doi", "Paper has no DOI")
    raw_metadata = json_loads(paper.get("raw_metadata"), {})
    if not isinstance(raw_metadata, dict):
        raw_metadata = {}
    try:
        result = await UnpaywallClient(settings.unpaywall_email, **unpaywall_client_options(settings)).resolve(normalized_doi)
        if result.get("error"):
            raw_metadata.pop("unpaywall", None)
            raw_metadata["oa_resolution_error"] = result["error"]
        else:
            raw_metadata.pop("oa_resolution_error", None)
            raw_metadata.pop("unpaywall", None)
            if isinstance(result.get("raw"), dict):
                raw_metadata["unpaywall"] = result["raw"]
    except Exception as exc:
        result = {"oa_status": "unknown", "oa_pdf_url": None}
        raw_metadata.pop("unpaywall", None)
        raw_metadata["oa_resolution_error"] = str(exc)
    with get_conn() as conn:
        conn.execute(
            "UPDATE papers SET doi=?, oa_status=?, oa_pdf_url=?, raw_metadata=?, updated_at=datetime('now') WHERE id=?",
            (normalized_doi, oa_status(result.get("oa_status")), web_url(result.get("oa_pdf_url")), json_dumps(raw_metadata), paper_id),
        )
    return get_paper(paper_id)


@router.post("/{paper_id}/classify", response_model=PaperDetailResponse)
def classify_paper(paper_id: int) -> dict:
    settings = get_settings()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM papers WHERE id=?", (paper_id,)).fetchone()
        if not row:
            raise AppError(404, "paper_not_found", "Paper not found")
        text = f"{row['title']} {row['abstract'] or ''}"
        categories = [dict_from_row(category_row) for category_row in conn.execute("SELECT * FROM categories").fetchall()]
        try:
            classified = get_classifier(settings).classify(text, categories)
        except Exception as exc:
            raise AppError(500, "paper_classification_failed", str(exc))
        registered_category_ids = {category["id"] for category in categories}
        conn.execute("DELETE FROM paper_categories WHERE paper_id=? AND method='auto'", (paper_id,))
        for item in classified:
            if item.get("category_id") not in registered_category_ids:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO paper_categories (paper_id, category_id, confidence, method)
                VALUES (?, ?, ?, 'auto')
                """,
                (paper_id, item["category_id"], item["confidence"]),
            )
    return get_paper(paper_id)


@router.put("/{paper_id}/categories", response_model=PaperDetailResponse)
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
