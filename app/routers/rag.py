from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from app.db import get_conn
from app.errors import AppError
from app.services.rag import query

router = APIRouter(prefix="/rag", tags=["rag"])


class RagQueryIn(BaseModel):
    question: str
    document_ids: list[int] = Field(default_factory=list)
    top_k: int = Field(6, ge=1, le=20)
    use_document_context: bool = False

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("question must not be blank")
        return normalized

    @field_validator("document_ids")
    @classmethod
    def document_ids_must_be_positive(cls, value: list[int]) -> list[int]:
        if any(item <= 0 for item in value):
            raise ValueError("document_ids must be positive integers")
        return value


class RagSourceResponse(BaseModel):
    document_id: int
    paper_id: Optional[int] = None
    paper_title: Optional[str] = None
    section_id: Optional[int] = None
    section_seq: Optional[int] = None
    section_title: Optional[str] = None
    section_type: Optional[str] = None
    chunk_id: Optional[int] = None
    vector_id: Optional[str] = None
    score: float
    source_excerpt: str


class RagResponse(BaseModel):
    answer: str
    sources: list[RagSourceResponse]


@router.post("/query", response_model=RagResponse)
def rag_query(body: RagQueryIn) -> dict:
    _ensure_documents_exist(body.document_ids)
    try:
        return query(
            body.question,
            body.document_ids,
            body.top_k,
            use_document_context=body.use_document_context,
        )
    except Exception as exc:
        raise AppError(500, "rag_query_failed", str(exc))


def _ensure_documents_exist(document_ids: list[int]) -> None:
    if not document_ids:
        return

    unique_ids = list(dict.fromkeys(document_ids))
    placeholders = ",".join("?" for _ in unique_ids)
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT id FROM documents WHERE id IN ({placeholders})",
            unique_ids,
        ).fetchall()

    found_ids = {row["id"] for row in rows}
    missing_ids = [document_id for document_id in unique_ids if document_id not in found_ids]
    if missing_ids:
        missing_id = missing_ids[0]
        raise AppError(404, "document_not_found", f"Document {missing_id} not found")
