import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from app.config import get_settings


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "docs" / "schema.sql"


def dict_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def connect() -> sqlite3.Connection:
    settings = get_settings()
    settings.ensure_dirs()
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    settings = get_settings()
    settings.ensure_dirs()
    should_init = not settings.database_path.exists()
    with connect() as conn:
        existing = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='journals'"
        ).fetchone()
        if should_init or existing is None:
            schema = SCHEMA_PATH.read_text(encoding="utf-8")
            conn.executescript(schema)
            conn.commit()


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_conn() as conn:
        return [dict_from_row(row) for row in conn.execute(sql, params).fetchall()]


def fetch_one(sql: str, params: tuple[Any, ...] = ()) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict_from_row(row) if row else None
