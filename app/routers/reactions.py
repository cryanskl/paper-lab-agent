from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Query
from pydantic import BaseModel, field_validator, model_validator

from app.db import dict_from_row, get_conn
from app.errors import AppError
from app.services.chemistry import export_reaction_set, reaction_set_detail, verify_reaction

router = APIRouter(tags=["reactions"])


ALLOWED_REACTION_TYPES = {"elastic", "excitation", "ionization", "attachment", "recombination"}
ALLOWED_RATE_TYPES = {"cross_section", "arrhenius", "constant"}


class VerifyIn(BaseModel):
    verified: bool
    reaction_type: Optional[str] = None
    rate_type: Optional[str] = None
    rate_value: Optional[str] = None
    threshold_ev: Optional[float] = None
    cross_section_url: Optional[str] = None
    verified_by: Optional[str] = None

    @field_validator("reaction_type", "rate_type", "rate_value", "cross_section_url")
    @classmethod
    def optional_text_fields_must_not_be_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("field must not be blank")
        return normalized

    @field_validator("verified_by")
    @classmethod
    def verified_by_must_not_be_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("verified_by must not be blank")
        return normalized

    @field_validator("threshold_ev")
    @classmethod
    def threshold_ev_must_not_be_negative(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("threshold_ev must be non-negative")
        return value

    @field_validator("reaction_type")
    @classmethod
    def reaction_type_must_be_known(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in ALLOWED_REACTION_TYPES:
            raise ValueError("reaction_type must be a known reaction type")
        return value

    @field_validator("rate_type")
    @classmethod
    def rate_type_must_be_known(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in ALLOWED_RATE_TYPES:
            raise ValueError("rate_type must be one of cross_section, arrhenius, constant")
        return value

    @field_validator("cross_section_url")
    @classmethod
    def cross_section_url_must_be_http_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("cross_section_url must be an HTTP URL")
        return value

    @model_validator(mode="after")
    def reviewer_required_for_verified_reaction(self) -> "VerifyIn":
        if self.verified_by is None:
            raise ValueError("verified_by is required for reaction review actions")
        return self


@router.get("/reaction-sets/{reaction_set_id}")
def get_reaction_set(reaction_set_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM reaction_sets WHERE id=?", (reaction_set_id,)).fetchone()
        if not row:
            raise AppError(404, "reaction_set_not_found", "Reaction set not found")
        return reaction_set_detail(dict_from_row(row), conn)


@router.put("/reactions/{reaction_id}/verify")
def verify(reaction_id: int, body: VerifyIn) -> dict:
    try:
        clear_fields = {
            field_name
            for field_name in {"reaction_type", "rate_type", "rate_value", "threshold_ev", "cross_section_url"}
            if field_name in body.model_fields_set and getattr(body, field_name) is None
        }
        return verify_reaction(
            reaction_id,
            body.verified,
            body.rate_value,
            body.verified_by,
            reaction_type=body.reaction_type,
            rate_type=body.rate_type,
            threshold_ev=body.threshold_ev,
            cross_section_url=body.cross_section_url,
            clear_fields=clear_fields,
        )
    except ValueError:
        raise AppError(404, "reaction_not_found", "Reaction not found")


@router.post("/reaction-sets/{reaction_set_id}/export")
def export(reaction_set_id: int, format: str = Query("json")) -> dict:
    try:
        return export_reaction_set(reaction_set_id, format)
    except PermissionError as exc:
        raise AppError(409, "reaction_set_unverified", str(exc))
    except ValueError as exc:
        if str(exc).startswith("unsupported export format"):
            raise AppError(400, "unsupported_export_format", str(exc))
        raise AppError(404, "reaction_set_not_found", "Reaction set not found")
