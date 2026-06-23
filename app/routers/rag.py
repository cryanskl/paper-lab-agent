from pydantic import BaseModel
from fastapi import APIRouter

from app.services.rag import query

router = APIRouter(prefix="/rag", tags=["rag"])


class RagQueryIn(BaseModel):
    question: str
    document_ids: list[int] = []
    top_k: int = 6


@router.post("/query")
def rag_query(body: RagQueryIn) -> dict:
    return query(body.question, body.document_ids, body.top_k)

