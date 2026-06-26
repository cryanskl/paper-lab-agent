import re
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field, field_validator

from app.db import dict_from_row, get_conn
from app.errors import AppError

router = APIRouter(prefix="/categories", tags=["categories"])

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class CategoryIn(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("field must not be blank")
        return normalized

    @field_validator("slug")
    @classmethod
    def slug_must_not_be_blank(cls, value: str) -> str:
        normalized = re.sub(r"\s+", "-", value.strip().lower())
        if not normalized:
            raise ValueError("field must not be blank")
        if SLUG_RE.fullmatch(normalized) is None:
            raise ValueError("slug must contain only lowercase letters, numbers, hyphens, or underscores")
        return normalized


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    children: list["CategoryResponse"] = Field(default_factory=list)


class CategoryListResponse(BaseModel):
    items: list[CategoryResponse]
    total: int
    page: int
    page_size: int


def serialize_categories(rows) -> list[dict]:
    categories = [dict_from_row(row) for row in rows]
    by_parent: dict[int, list[dict]] = {}
    for category in categories:
        category["children"] = []
        parent_id = category.get("parent_id")
        if parent_id is not None:
            by_parent.setdefault(parent_id, []).append(category)
    for category in categories:
        category["children"] = by_parent.get(category["id"], [])
    return categories


@router.get("", response_model=CategoryListResponse)
def list_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM categories ORDER BY id").fetchall()
    all_items = serialize_categories(rows)
    offset = (page - 1) * page_size
    items = all_items[offset : offset + page_size]
    return {"items": items, "total": len(all_items), "page": page, "page_size": page_size}


@router.post("", status_code=201, response_model=CategoryResponse)
def create_category(body: CategoryIn) -> dict:
    try:
        with get_conn() as conn:
            if body.parent_id is not None:
                parent = conn.execute("SELECT id FROM categories WHERE id=?", (body.parent_id,)).fetchone()
                if parent is None:
                    raise AppError(404, "category_parent_not_found", "Parent category not found")
            cursor = conn.execute(
                "INSERT INTO categories (name, slug, description, parent_id) VALUES (?, ?, ?, ?)",
                (body.name, body.slug, body.description, body.parent_id),
            )
            row = conn.execute("SELECT * FROM categories WHERE id=?", (cursor.lastrowid,)).fetchone()
    except AppError:
        raise
    except Exception as exc:
        raise AppError(409, "category_conflict", str(exc))
    category = dict_from_row(row)
    category["children"] = []
    return category
