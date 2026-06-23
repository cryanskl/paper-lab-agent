from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db import dict_from_row, get_conn
from app.errors import AppError
from app.services.chemistry import export_reaction_set, reaction_set_detail, verify_reaction

router = APIRouter(tags=["reactions"])


class VerifyIn(BaseModel):
    verified: bool
    rate_value: Optional[str] = None
    verified_by: Optional[str] = None


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
        return verify_reaction(reaction_id, body.verified, body.rate_value, body.verified_by)
    except ValueError:
        raise AppError(404, "reaction_not_found", "Reaction not found")


@router.post("/reaction-sets/{reaction_set_id}/export")
def export(reaction_set_id: int, format: str = Query("json")) -> dict:
    try:
        return export_reaction_set(reaction_set_id, format)
    except PermissionError as exc:
        raise AppError(409, "reaction_set_unverified", str(exc))
    except ValueError:
        raise AppError(404, "reaction_set_not_found", "Reaction set not found")

