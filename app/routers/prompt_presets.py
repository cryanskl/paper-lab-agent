import re
import sqlite3
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field, field_validator

from app.db import dict_from_row, get_conn
from app.errors import AppError, page

router = APIRouter(prefix="/prompt-presets", tags=["prompt-presets"])

COMMAND_RE = re.compile(r"^/[^\s/]{1,23}$")


def normalize_command(value: str) -> str:
    normalized = value.strip()
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if COMMAND_RE.fullmatch(normalized) is None:
        raise ValueError("command must start with '/', contain no spaces, and be at most 24 characters")
    return normalized


class PromptPresetIn(BaseModel):
    command: str = Field(max_length=24)
    description: Optional[str] = Field(default=None, max_length=80)
    prompt: str = Field(max_length=1000)

    @field_validator("command")
    @classmethod
    def command_must_match_contract(cls, value: str) -> str:
        return normalize_command(value)

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("prompt must not be blank")
        return normalized


class PromptPresetResponse(BaseModel):
    id: int
    command: str
    description: Optional[str] = None
    prompt: str
    created_at: str
    updated_at: str


class PromptPresetListResponse(BaseModel):
    items: list[PromptPresetResponse]
    total: int
    page: int
    page_size: int


class PromptPresetDeleteResponse(BaseModel):
    id: int
    command: str


def preset_conflict(exc: sqlite3.IntegrityError) -> AppError:
    return AppError(409, "prompt_preset_conflict", "A preset with this command already exists")


@router.get("", response_model=PromptPresetListResponse)
def list_prompt_presets(
    page_num: int = Query(1, alias="page", ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    offset = (page_num - 1) * page_size
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM prompt_presets").fetchone()["n"]
        rows = conn.execute(
            "SELECT * FROM prompt_presets ORDER BY id LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()
    return page([dict_from_row(row) for row in rows], total, page_num, page_size)


@router.post("", status_code=201, response_model=PromptPresetResponse)
def create_prompt_preset(body: PromptPresetIn) -> dict:
    try:
        with get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO prompt_presets (command, description, prompt)
                VALUES (?, ?, ?)
                """,
                (body.command, body.description, body.prompt),
            )
            row = conn.execute("SELECT * FROM prompt_presets WHERE id=?", (cursor.lastrowid,)).fetchone()
    except sqlite3.IntegrityError as exc:
        raise preset_conflict(exc) from exc
    return dict_from_row(row)


@router.put("/{preset_id}", response_model=PromptPresetResponse)
def update_prompt_preset(preset_id: int, body: PromptPresetIn) -> dict:
    try:
        with get_conn() as conn:
            existing = conn.execute("SELECT id FROM prompt_presets WHERE id=?", (preset_id,)).fetchone()
            if existing is None:
                raise AppError(404, "prompt_preset_not_found", "Prompt preset not found")
            conn.execute(
                """
                UPDATE prompt_presets
                SET command=?, description=?, prompt=?, updated_at=datetime('now')
                WHERE id=?
                """,
                (body.command, body.description, body.prompt, preset_id),
            )
            row = conn.execute("SELECT * FROM prompt_presets WHERE id=?", (preset_id,)).fetchone()
    except sqlite3.IntegrityError as exc:
        raise preset_conflict(exc) from exc
    return dict_from_row(row)


@router.delete("/{preset_id}", response_model=PromptPresetDeleteResponse)
def delete_prompt_preset(preset_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT id, command FROM prompt_presets WHERE id=?", (preset_id,)).fetchone()
        if row is None:
            raise AppError(404, "prompt_preset_not_found", "Prompt preset not found")
        conn.execute("DELETE FROM prompt_presets WHERE id=?", (preset_id,))
    return dict_from_row(row)
