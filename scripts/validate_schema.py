#!/usr/bin/env python3
"""Validate the SQLite schema truth source in docs/schema.sql."""

from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA_PATH = REPO_ROOT / "docs" / "schema.sql"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

REQUIRED_TABLES = [
    "journals",
    "papers",
    "categories",
    "paper_categories",
    "crawl_jobs",
    "documents",
    "sections",
    "translations",
    "chunks",
    "reaction_sets",
    "reactions",
    "reaction_audits",
]
REQUIRED_INDEXES = [
    "idx_papers_journal",
    "idx_papers_year",
    "idx_papers_oa",
    "idx_crawljobs_journal",
    "idx_documents_paper",
    "idx_sections_doc",
    "idx_translations_doc",
    "idx_chunks_doc",
    "idx_rsets_doc",
    "idx_reactions_set",
    "idx_reaction_audits_reaction",
]
REQUIRED_TRIGGERS = ["papers_ai", "papers_ad", "papers_au"]
SEED_COUNTS = {"journals": 6, "categories": 7}
REQUIRED_COLUMNS = {
    "journals": [
        "id",
        "name",
        "publisher",
        "platform",
        "url",
        "issn_print",
        "issn_electronic",
        "keywords",
        "year_from",
        "year_to",
        "sci_zone",
        "impact_factor",
        "active",
    ],
    "papers": [
        "id",
        "doi",
        "title",
        "abstract",
        "authors",
        "journal_id",
        "journal_name",
        "published_date",
        "published_year",
        "landing_url",
        "oa_status",
        "oa_pdf_url",
        "source_api",
        "dedupe_key",
        "raw_metadata",
        "indexed_at",
        "updated_at",
    ],
    "categories": [
        "id",
        "name",
        "slug",
        "description",
        "parent_id",
    ],
    "paper_categories": [
        "paper_id",
        "category_id",
        "confidence",
        "method",
        "created_at",
    ],
    "crawl_jobs": [
        "id",
        "journal_id",
        "period",
        "date_from",
        "date_to",
        "status",
        "papers_found",
        "papers_filtered",
        "papers_new",
        "error",
        "started_at",
        "finished_at",
        "created_at",
    ],
    "documents": [
        "id",
        "paper_id",
        "file_path",
        "file_hash",
        "original_name",
        "parse_status",
        "parse_error",
        "index_status",
        "index_error",
        "chemistry_status",
        "chemistry_error",
        "tei_path",
    ],
    "sections": [
        "id",
        "document_id",
        "parent_id",
        "seq",
        "title",
        "content",
        "section_type",
    ],
    "translations": [
        "id",
        "document_id",
        "source_lang",
        "target_lang",
        "status",
        "output_path",
        "error",
    ],
    "chunks": [
        "id",
        "document_id",
        "section_id",
        "seq",
        "text",
        "token_count",
        "vector_id",
        "embedded",
    ],
    "reaction_sets": [
        "id",
        "document_id",
        "name",
        "gas_mixture",
        "lxcat_db",
        "source_note",
        "status",
        "verified_by",
        "verified_at",
    ],
    "reactions": [
        "id",
        "reaction_set_id",
        "reaction",
        "reaction_type",
        "reactants",
        "products",
        "rate_type",
        "rate_value",
        "threshold_ev",
        "reference",
        "cross_section_url",
        "source_section_id",
        "source_label",
        "source_excerpt",
        "confidence",
        "verified",
    ],
    "reaction_audits": [
        "id",
        "reaction_id",
        "action",
        "changes",
        "verified_by",
        "created_at",
    ],
}


def sqlite_names(conn: sqlite3.Connection, object_type: str) -> set[str]:
    return {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type=? ORDER BY name", (object_type,)).fetchall()
    }


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def validate_fts(conn: sqlite3.Connection) -> list[str]:
    issues: list[str] = []
    try:
        conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, '[]', 'schema-validator', '{}')
            """,
            ("Schema validator plasma paper", "low temperature plasma",),
        )
        row = conn.execute(
            """
            SELECT rowid
            FROM papers_fts
            WHERE papers_fts MATCH ?
            """,
            ("plasma",),
        ).fetchone()
    except sqlite3.Error as exc:
        issues.append(f"papers_fts query failed: {exc}")
        return issues
    if row is None:
        issues.append("papers_fts did not index inserted paper")
    return issues


def validate_connection_schema(conn: sqlite3.Connection, *, require_seed_counts: bool) -> list[str]:
    issues: list[str] = []
    foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    if foreign_keys != 1:
        issues.append("PRAGMA foreign_keys must be ON")

    tables = sqlite_names(conn, "table")
    indexes = sqlite_names(conn, "index")
    triggers = sqlite_names(conn, "trigger")
    for table in REQUIRED_TABLES:
        if table not in tables:
            issues.append(f"missing table: {table}")
    if "papers_fts" not in tables:
        issues.append("missing table: papers_fts")
    for index in REQUIRED_INDEXES:
        if index not in indexes:
            issues.append(f"missing index: {index}")
    for trigger in REQUIRED_TRIGGERS:
        if trigger not in triggers:
            issues.append(f"missing trigger: {trigger}")
    for table, columns in REQUIRED_COLUMNS.items():
        if table not in tables:
            continue
        existing_columns = table_columns(conn, table)
        for column in columns:
            if column not in existing_columns:
                issues.append(f"missing column: {table}.{column}")

    if require_seed_counts:
        for table, expected_count in SEED_COUNTS.items():
            if table in tables:
                actual_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                if actual_count != expected_count:
                    issues.append(f"seed count mismatch: {table}={actual_count}, expected {expected_count}")

    if "papers" in tables and "papers_fts" in tables and set(REQUIRED_TRIGGERS).issubset(triggers):
        issues.extend(validate_fts(conn))
    return issues


def create_legacy_partial_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE journals (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE papers (id INTEGER PRIMARY KEY, title TEXT);
        CREATE TABLE categories (id INTEGER PRIMARY KEY);
        CREATE TABLE paper_categories (paper_id INTEGER, category_id INTEGER);
        CREATE TABLE crawl_jobs (id INTEGER PRIMARY KEY);
        CREATE TABLE documents (id INTEGER PRIMARY KEY, file_path TEXT NOT NULL);
        CREATE TABLE sections (id INTEGER PRIMARY KEY);
        CREATE TABLE translations (id INTEGER PRIMARY KEY);
        CREATE TABLE chunks (id INTEGER PRIMARY KEY);
        CREATE TABLE reaction_sets (id INTEGER PRIMARY KEY);
        CREATE TABLE reactions (id INTEGER PRIMARY KEY, reaction_set_id INTEGER, reaction TEXT);
        """
    )
    conn.commit()


def validate_migrations() -> list[str]:
    issues: list[str] = []
    with tempfile.TemporaryDirectory(prefix="paper-lab-migration-") as temp_dir:
        database_path = Path(temp_dir) / "legacy.db"
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            create_legacy_partial_schema(conn)
            from app.db import ensure_migrations

            ensure_migrations(conn)
            issues.extend(validate_connection_schema(conn, require_seed_counts=False))
        except sqlite3.Error as exc:
            issues.append(f"migration validation failed: {exc}")
        finally:
            conn.close()
    return issues


def first_symlink_parent(path: Path) -> Path | None:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        return parent
    return None


def validate_schema(schema_path: Path = DEFAULT_SCHEMA_PATH) -> list[str]:
    issues: list[str] = []
    if not schema_path.exists():
        return [f"schema not found: {schema_path}"]
    symlink_parent = first_symlink_parent(schema_path)
    if symlink_parent is not None:
        return [f"schema file parent is not a regular directory: {symlink_parent}"]
    if schema_path.is_symlink() or not schema_path.is_file():
        return [f"schema file is not a regular file: {schema_path}"]

    with tempfile.TemporaryDirectory(prefix="paper-lab-schema-") as temp_dir:
        database_path = Path(temp_dir) / "schema.db"
        conn = sqlite3.connect(database_path)
        try:
            try:
                schema_sql = schema_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                issues.append(f"schema file unreadable: {schema_path}: {exc}")
                return issues
            conn.executescript(schema_sql)
            issues.extend(validate_connection_schema(conn, require_seed_counts=True))
        except sqlite3.Error as exc:
            issues.append(f"schema execution failed: {exc}")
        finally:
            conn.close()
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate docs/schema.sql against release expectations.")
    parser.add_argument("schema_path", nargs="?", default=str(DEFAULT_SCHEMA_PATH))
    args = parser.parse_args()

    issues = validate_schema(Path(args.schema_path))
    issues.extend(validate_migrations())
    if issues:
        print("schema validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
