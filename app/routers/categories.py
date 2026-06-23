from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.db import dict_from_row, get_conn
from app.errors import AppError

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryIn(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[int] = None


@router.get("")
def list_categories() -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM categories ORDER BY id").fetchall()
    return {"items": [dict_from_row(row) for row in rows]}


@router.post("", status_code=201)
def create_category(body: CategoryIn) -> dict:
    try:
        with get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO categories (name, slug, description, parent_id) VALUES (?, ?, ?, ?)",
                (body.name, body.slug, body.description, body.parent_id),
            )
            row = conn.execute("SELECT * FROM categories WHERE id=?", (cursor.lastrowid,)).fetchone()
    except Exception as exc:
        raise AppError(409, "category_conflict", str(exc))
    return dict_from_row(row)

