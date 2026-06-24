from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter

from app.services.rag import query

router = APIRouter(prefix="/rag", tags=["rag"])


class RagQueryIn(BaseModel):
    question: str
    document_ids: list[int] = Field(default_factory=list)
    top_k: int = Field(6, ge=1, le=20)

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


@router.post("/query")
def rag_query(body: RagQueryIn) -> dict:
    return query(body.question, body.document_ids, body.top_k)
