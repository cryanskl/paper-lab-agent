from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field, field_validator

from app.db import dict_from_row, get_conn
from app.errors import AppError
from app.services.translation import create_term_translation_job, translate_term


router = APIRouter(prefix="/term-translations", tags=["translations"])


def normalize_language(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("language must not be blank")
    if len(normalized) > 24:
        raise ValueError("language must not exceed 24 characters")
    if any(char in normalized for char in ("/", "\\")):
        raise ValueError("language must not contain path separators")
    if any(ord(char) < 32 for char in normalized):
        raise ValueError("language must not contain control characters")
    return normalized


class TermTranslationIn(BaseModel):
    source_text: str = Field(min_length=1, max_length=120)
    source_lang: str
    target_lang: str
    context_text: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("source_text")
    @classmethod
    def source_text_must_not_be_blank(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("source_text must not be blank")
        return normalized

    @field_validator("source_lang", "target_lang")
    @classmethod
    def languages_must_be_safe(cls, value: str) -> str:
        return normalize_language(value)

    @field_validator("context_text")
    @classmethod
    def context_must_be_normalized(cls, value: Optional[str]) -> Optional[str]:
        normalized = " ".join((value or "").split())
        return normalized or None


class TermTranslationJobResponse(BaseModel):
    job_id: int
    source_text: str
    source_lang: str
    target_lang: str
    status: str


class TermTranslationResponse(BaseModel):
    id: int
    source_text: str
    source_lang: str
    target_lang: str
    context_text: Optional[str] = None
    target_text: Optional[str] = None
    status: str
    error: Optional[str] = None
    created_at: str
    updated_at: str


@router.post("", status_code=202, response_model=TermTranslationJobResponse)
def start_term_translation(body: TermTranslationIn, background_tasks: BackgroundTasks) -> dict:
    if body.source_lang.casefold() == body.target_lang.casefold():
        raise AppError(422, "validation_error", "source_lang and target_lang must differ")
    translation, cached = create_term_translation_job(
        body.source_text,
        body.source_lang,
        body.target_lang,
        body.context_text,
    )
    if not cached:
        background_tasks.add_task(translate_term, translation["id"])
    return {
        "job_id": translation["id"],
        "source_text": translation["source_text"],
        "source_lang": translation["source_lang"],
        "target_lang": translation["target_lang"],
        "status": translation["status"],
    }


@router.get("/{translation_id}", response_model=TermTranslationResponse)
def get_term_translation(translation_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM term_translations WHERE id=?",
            (translation_id,),
        ).fetchone()
    if row is None:
        raise AppError(404, "term_translation_not_found", "Term translation not found")
    return dict_from_row(row)
