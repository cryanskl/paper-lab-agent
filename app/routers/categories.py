import re
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field, field_validator

from app.db import dict_from_row, get_conn
from app.errors import AppError

router = APIRouter(prefix="/categories", tags=["categories"])

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class CategoryFields(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None

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

    @field_validator("description")
    @classmethod
    def optional_text_is_trimmed(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CategoryIn(CategoryFields):
    parent_id: Optional[int] = None


class CategoryUpdateIn(CategoryFields):
    pass


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    paper_count: int = 0
    children: list["CategoryResponse"] = Field(default_factory=list)


class CategoryListResponse(BaseModel):
    items: list[CategoryResponse]
    total: int
    page: int
    page_size: int


class CategoryDeleteResponse(BaseModel):
    id: int
    name: str
    slug: str
    removed_paper_links: int


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


def get_serialized_category(conn, category_id: int) -> dict:
    rows = conn.execute(
        """
        SELECT c.*, COUNT(pc.paper_id) AS paper_count
        FROM categories c
        LEFT JOIN paper_categories pc ON pc.category_id = c.id
        GROUP BY c.id
        ORDER BY c.id
        """
    ).fetchall()
    category = next(
        (item for item in serialize_categories(rows) if item["id"] == category_id),
        None,
    )
    if category is None:
        raise AppError(404, "category_not_found", "Category not found")
    return category


@router.get("", response_model=CategoryListResponse)
def list_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT c.*, COUNT(pc.paper_id) AS paper_count
            FROM categories c
            LEFT JOIN paper_categories pc ON pc.category_id = c.id
            GROUP BY c.id
            ORDER BY c.id
            """
        ).fetchall()
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
    category["paper_count"] = 0
    category["children"] = []
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, body: CategoryUpdateIn) -> dict:
    try:
        with get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM categories WHERE id=?",
                (category_id,),
            ).fetchone()
            if existing is None:
                raise AppError(404, "category_not_found", "Category not found")
            conn.execute(
                """
                UPDATE categories
                SET name=?, slug=?, description=?
                WHERE id=?
                """,
                (body.name, body.slug, body.description, category_id),
            )
            category = get_serialized_category(conn, category_id)
    except AppError:
        raise
    except Exception as exc:
        raise AppError(409, "category_conflict", str(exc))
    return category


@router.delete("/{category_id}", response_model=CategoryDeleteResponse)
def delete_category(category_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()
        if row is None:
            raise AppError(404, "category_not_found", "Category not found")
        child = conn.execute("SELECT id FROM categories WHERE parent_id=? LIMIT 1", (category_id,)).fetchone()
        if child is not None:
            raise AppError(
                409,
                "category_has_children",
                "Category has child categories; delete or reassign them first",
            )
        removed_paper_links = conn.execute(
            "SELECT COUNT(*) AS n FROM paper_categories WHERE category_id=?",
            (category_id,),
        ).fetchone()["n"]
        category = dict_from_row(row)
        conn.execute("DELETE FROM categories WHERE id=?", (category_id,))
    return {
        "id": category["id"],
        "name": category["name"],
        "slug": category["slug"],
        "removed_paper_links": removed_paper_links,
    }
