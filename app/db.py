import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

from app.config import get_settings


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "docs" / "schema.sql"

DEFAULT_PROMPT_PRESETS = [
    ("/总结", "总结当前范围内文献的核心结论", "总结当前范围内文献的核心结论、方法与主要数据。"),
    ("/术语", "提取并解释文中的专业术语", "提取当前范围文献中的关键专业术语，并逐条解释其含义。"),
    ("/相关工作", "梳理相关工作与研究脉络", "梳理当前范围文献涉及的相关工作与研究脉络。"),
    ("/提问我", "就所选文献向我提问，考察理解", "就当前范围的文献内容，向我提出两个考察理解的问题。"),
]

DEFAULT_GLOSSARY_TERMS = [
    ("capacitively coupled", "容性耦合"),
    ("electron energy distribution function", "电子能量分布函数"),
    ("EEDF", "电子能量分布函数"),
    ("particle-in-cell", "粒子网格法"),
    ("Monte Carlo collisions", "蒙特卡罗碰撞"),
    ("secondary electron emission", "二次电子发射"),
    ("ohmic heating", "欧姆加热"),
    ("cross section", "截面"),
    ("dissociation", "解离"),
    ("ionization", "电离"),
    ("attachment", "吸附"),
    ("radical", "自由基"),
    ("ion flux", "离子通量"),
    ("sheath", "鞘层"),
    ("self-bias", "自偏压"),
    ("rate coefficient", "速率系数"),
]


def dict_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def assert_safe_database_path(path: Path) -> None:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        raise OSError(f"database path parent is not a regular directory: {parent}")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise OSError(f"database path is not a regular file: {path}")


def connect() -> sqlite3.Connection:
    settings = get_settings()
    settings.ensure_dirs()
    assert_safe_database_path(settings.database_path)
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
        ensure_migrations(conn)


def make_schema_statement_idempotent(statement: str) -> str:
    normalized = statement.strip()
    replacements = [
        ("CREATE VIRTUAL TABLE ", "CREATE VIRTUAL TABLE IF NOT EXISTS "),
        ("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS "),
        ("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS "),
        ("CREATE TRIGGER ", "CREATE TRIGGER IF NOT EXISTS "),
    ]
    for prefix, replacement in replacements:
        if normalized.startswith(prefix) and not normalized.startswith(replacement):
            return replacement + normalized[len(prefix) :]
    return normalized


def ensure_schema_objects(conn: sqlite3.Connection) -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    ddl = "\n".join(line for line in schema.splitlines() if not line.strip().startswith("--"))
    for statement in ddl.split(";"):
        normalized = statement.strip()
        if not normalized.startswith("CREATE TABLE "):
            continue
        conn.execute(make_schema_statement_idempotent(normalized))
    conn.commit()


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def create_index_if_columns_exist(conn: sqlite3.Connection, index_name: str, table: str, columns: list[str]) -> None:
    existing_columns = table_columns(conn, table)
    if set(columns).issubset(existing_columns):
        conn.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({', '.join(columns)})")


def ensure_schema_indexes(conn: sqlite3.Connection) -> None:
    index_specs = [
        ("idx_papers_journal", "papers", ["journal_id"]),
        ("idx_papers_year", "papers", ["published_year"]),
        ("idx_papers_oa", "papers", ["oa_status"]),
        ("idx_papers_library_status", "papers", ["library_status"]),
        ("idx_crawljobs_journal", "crawl_jobs", ["journal_id"]),
        ("idx_search_history_cache", "search_history", ["cache_key", "status", "finished_at"]),
        ("idx_search_results_search", "search_results", ["search_history_id"]),
        ("idx_search_results_paper", "search_results", ["paper_id"]),
        ("idx_documents_paper", "documents", ["paper_id"]),
        ("idx_paper_downloads_status", "paper_downloads", ["status"]),
        ("idx_sections_doc", "sections", ["document_id"]),
        ("idx_translations_doc", "translations", ["document_id"]),
        (
            "idx_paper_abstract_translations_paper",
            "paper_abstract_translations",
            ["paper_id", "target_lang", "id"],
        ),
        (
            "idx_term_translations_lookup",
            "term_translations",
            ["source_text", "source_lang", "target_lang", "status", "id"],
        ),
        ("idx_glossary_terms_en", "glossary_terms", ["en"]),
        ("idx_glossary_terms_zh", "glossary_terms", ["zh"]),
        ("idx_chunks_doc", "chunks", ["document_id"]),
        ("idx_rsets_doc", "reaction_sets", ["document_id"]),
        ("idx_reactions_set", "reactions", ["reaction_set_id"]),
        ("idx_reaction_audits_reaction", "reaction_audits", ["reaction_id"]),
    ]
    for index_name, table, columns in index_specs:
        create_index_if_columns_exist(conn, index_name, table, columns)
    conn.commit()


def ensure_migrations(conn: sqlite3.Connection) -> None:
    prompt_presets_existed = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='prompt_presets'"
    ).fetchone() is not None
    glossary_terms_existed = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='glossary_terms'"
    ).fetchone() is not None
    ensure_schema_objects(conn)
    if not prompt_presets_existed:
        conn.executemany(
            """
            INSERT INTO prompt_presets (command, description, prompt)
            VALUES (?, ?, ?)
            """,
            DEFAULT_PROMPT_PRESETS,
        )
        conn.commit()
    if not glossary_terms_existed:
        conn.executemany(
            "INSERT INTO glossary_terms (en, zh) VALUES (?, ?)",
            DEFAULT_GLOSSARY_TERMS,
        )
        conn.commit()
    journal_columns = {row["name"] for row in conn.execute("PRAGMA table_info(journals)").fetchall()}
    journal_column_specs = {
        "publisher": "TEXT",
        "platform": "TEXT",
        "url": "TEXT",
        "issn_print": "TEXT",
        "issn_electronic": "TEXT",
        "keywords": "TEXT",
        "year_from": "INTEGER DEFAULT 1990",
        "year_to": "INTEGER",
        "sci_zone": "TEXT",
        "impact_factor": "REAL",
        "active": "INTEGER DEFAULT 1",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    }
    for column, spec in journal_column_specs.items():
        if column not in journal_columns:
            conn.execute(f"ALTER TABLE journals ADD COLUMN {column} {spec}")
            conn.commit()
            journal_columns.add(column)
    category_columns = {row["name"] for row in conn.execute("PRAGMA table_info(categories)").fetchall()}
    category_column_specs = {
        "name": "TEXT",
        "slug": "TEXT",
        "description": "TEXT",
        "parent_id": "INTEGER REFERENCES categories(id)",
    }
    for column, spec in category_column_specs.items():
        if column not in category_columns:
            conn.execute(f"ALTER TABLE categories ADD COLUMN {column} {spec}")
            conn.commit()
            category_columns.add(column)
    category_unique_indexes = conn.execute("PRAGMA index_list(categories)").fetchall()
    has_unique_category_slug_index = False
    for index in category_unique_indexes:
        if not index["unique"]:
            continue
        index_columns = [
            row["name"] for row in conn.execute(f"PRAGMA index_info({index['name']})").fetchall()
        ]
        if index_columns == ["slug"]:
            has_unique_category_slug_index = True
            break
    duplicate_slug = conn.execute(
        """
        SELECT slug
        FROM categories
        WHERE slug IS NOT NULL
        GROUP BY slug
        HAVING COUNT(*) > 1
        LIMIT 1
        """
    ).fetchone()
    if not has_unique_category_slug_index and duplicate_slug is None:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug)")
        conn.commit()
    paper_category_columns = {row["name"] for row in conn.execute("PRAGMA table_info(paper_categories)").fetchall()}
    paper_category_column_specs = {
        "paper_id": "INTEGER REFERENCES papers(id) ON DELETE CASCADE",
        "category_id": "INTEGER REFERENCES categories(id) ON DELETE CASCADE",
        "confidence": "REAL",
        "method": "TEXT DEFAULT 'auto'",
        "created_at": "TEXT",
    }
    for column, spec in paper_category_column_specs.items():
        if column not in paper_category_columns:
            conn.execute(f"ALTER TABLE paper_categories ADD COLUMN {column} {spec}")
            conn.commit()
            paper_category_columns.add(column)
    paper_category_unique_indexes = conn.execute("PRAGMA index_list(paper_categories)").fetchall()
    has_unique_paper_category_index = False
    for index in paper_category_unique_indexes:
        if not index["unique"]:
            continue
        index_columns = [
            row["name"] for row in conn.execute(f"PRAGMA index_info({index['name']})").fetchall()
        ]
        if index_columns == ["paper_id", "category_id"]:
            has_unique_paper_category_index = True
            break
    duplicate_paper_category = conn.execute(
        """
        SELECT paper_id, category_id
        FROM paper_categories
        WHERE paper_id IS NOT NULL AND category_id IS NOT NULL
        GROUP BY paper_id, category_id
        HAVING COUNT(*) > 1
        LIMIT 1
        """
    ).fetchone()
    if not has_unique_paper_category_index and duplicate_paper_category is None:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_paper_categories_pair ON paper_categories(paper_id, category_id)"
        )
        conn.commit()
    crawl_job_columns = {row["name"] for row in conn.execute("PRAGMA table_info(crawl_jobs)").fetchall()}
    crawl_job_column_specs = {
        "journal_id": "INTEGER REFERENCES journals(id)",
        "period": "TEXT",
        "date_from": "TEXT",
        "date_to": "TEXT",
        "status": "TEXT DEFAULT 'pending'",
        "papers_found": "INTEGER DEFAULT 0",
        "papers_filtered": "INTEGER DEFAULT 0",
        "papers_new": "INTEGER DEFAULT 0",
        "search_terms": "TEXT",
        "search_mode": "TEXT",
        "max_results": "INTEGER",
        "search_history_id": "INTEGER",
        "error": "TEXT",
        "started_at": "TEXT",
        "finished_at": "TEXT",
        "created_at": "TEXT",
    }
    for column, spec in crawl_job_column_specs.items():
        if column not in crawl_job_columns:
            conn.execute(f"ALTER TABLE crawl_jobs ADD COLUMN {column} {spec}")
            conn.commit()
            crawl_job_columns.add(column)
    paper_columns = {row["name"] for row in conn.execute("PRAGMA table_info(papers)").fetchall()}
    paper_column_specs = {
        "doi": "TEXT",
        "abstract": "TEXT",
        "authors": "TEXT",
        "journal_id": "INTEGER REFERENCES journals(id)",
        "journal_name": "TEXT",
        "published_date": "TEXT",
        "published_year": "INTEGER",
        "landing_url": "TEXT",
        "oa_status": "TEXT",
        "oa_pdf_url": "TEXT",
        "source_api": "TEXT",
        "dedupe_key": "TEXT",
        "raw_metadata": "TEXT",
        "library_status": "TEXT NOT NULL DEFAULT 'saved'",
        "indexed_at": "TEXT",
        "updated_at": "TEXT",
    }
    for column, spec in paper_column_specs.items():
        if column not in paper_columns:
            conn.execute(f"ALTER TABLE papers ADD COLUMN {column} {spec}")
            conn.commit()
            paper_columns.add(column)
    search_history_columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(search_history)").fetchall()
    }
    search_history_column_specs = {
        "decision_status": "TEXT NOT NULL DEFAULT 'saved'",
        "new_result_count": "INTEGER DEFAULT 0",
        "saved_at": "TEXT",
        "discarded_at": "TEXT",
    }
    for column, spec in search_history_column_specs.items():
        if column not in search_history_columns:
            conn.execute(f"ALTER TABLE search_history ADD COLUMN {column} {spec}")
            conn.commit()
            search_history_columns.add(column)
    paper_unique_indexes = conn.execute("PRAGMA index_list(papers)").fetchall()
    has_unique_dedupe_key_index = False
    for index in paper_unique_indexes:
        if not index["unique"]:
            continue
        index_columns = [
            row["name"] for row in conn.execute(f"PRAGMA index_info({index['name']})").fetchall()
        ]
        if index_columns == ["dedupe_key"]:
            has_unique_dedupe_key_index = True
            break
    duplicate_dedupe_key = conn.execute(
        """
        SELECT dedupe_key
        FROM papers
        WHERE dedupe_key IS NOT NULL
        GROUP BY dedupe_key
        HAVING COUNT(*) > 1
        LIMIT 1
        """
    ).fetchone()
    if not has_unique_dedupe_key_index and duplicate_dedupe_key is None:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_dedupe_key ON papers(dedupe_key)")
        conn.commit()
    papers_fts = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='papers_fts'").fetchone()
    expected_fts_columns = ["title", "abstract", "authors", "doi"]
    fts_can_sync = set(expected_fts_columns).issubset(paper_columns)
    fts_needs_rebuild = False
    if papers_fts is not None:
        existing_fts_columns = [
            row["name"]
            for row in conn.execute("PRAGMA table_info(papers_fts)").fetchall()
            if row["name"]
        ]
        if existing_fts_columns != expected_fts_columns:
            conn.executescript(
                """
                DROP TRIGGER IF EXISTS papers_ai;
                DROP TRIGGER IF EXISTS papers_ad;
                DROP TRIGGER IF EXISTS papers_au;
                DROP TABLE papers_fts;
                """
            )
            papers_fts = None
    if papers_fts is None and fts_can_sync:
        conn.execute(
            """
            CREATE VIRTUAL TABLE papers_fts USING fts5(
                title, abstract, authors, doi,
                content='papers', content_rowid='id',
                tokenize='unicode61'
            )
            """
        )
        fts_needs_rebuild = True
    if fts_can_sync:
        conn.executescript(
            """
            DROP TRIGGER IF EXISTS papers_ai;
            DROP TRIGGER IF EXISTS papers_ad;
            DROP TRIGGER IF EXISTS papers_au;
            CREATE TRIGGER papers_ai AFTER INSERT ON papers BEGIN
                INSERT INTO papers_fts(rowid, title, abstract, authors, doi)
                VALUES (new.id, new.title, new.abstract, new.authors, new.doi);
            END;
            CREATE TRIGGER papers_ad AFTER DELETE ON papers BEGIN
                INSERT INTO papers_fts(papers_fts, rowid, title, abstract, authors, doi)
                VALUES ('delete', old.id, old.title, old.abstract, old.authors, old.doi);
            END;
            CREATE TRIGGER papers_au AFTER UPDATE ON papers BEGIN
                INSERT INTO papers_fts(papers_fts, rowid, title, abstract, authors, doi)
                VALUES ('delete', old.id, old.title, old.abstract, old.authors, old.doi);
                INSERT INTO papers_fts(rowid, title, abstract, authors, doi)
                VALUES (new.id, new.title, new.abstract, new.authors, new.doi);
            END;
            """
        )
    if fts_can_sync and fts_needs_rebuild:
        conn.execute("INSERT INTO papers_fts(papers_fts) VALUES ('rebuild')")
        conn.commit()
    document_columns = {row["name"] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
    document_column_specs = {
        "paper_id": "INTEGER REFERENCES papers(id)",
        "file_hash": "TEXT",
        "original_name": "TEXT",
        "num_pages": "INTEGER",
        "parse_status": "TEXT DEFAULT 'uploaded'",
        "parse_error": "TEXT",
        "index_status": "TEXT DEFAULT 'not_indexed'",
        "index_error": "TEXT",
        "chemistry_status": "TEXT DEFAULT 'not_extracted'",
        "chemistry_error": "TEXT",
        "tei_path": "TEXT",
        "created_at": "TEXT",
    }
    for column, spec in document_column_specs.items():
        if column not in document_columns:
            conn.execute(f"ALTER TABLE documents ADD COLUMN {column} {spec}")
            conn.commit()
            document_columns.add(column)
    document_unique_indexes = conn.execute("PRAGMA index_list(documents)").fetchall()
    has_unique_file_hash_index = False
    for index in document_unique_indexes:
        if not index["unique"]:
            continue
        index_columns = [
            row["name"] for row in conn.execute(f"PRAGMA index_info({index['name']})").fetchall()
        ]
        if index_columns == ["file_hash"]:
            has_unique_file_hash_index = True
            break
    duplicate_file_hash = conn.execute(
        """
        SELECT file_hash
        FROM documents
        WHERE file_hash IS NOT NULL
        GROUP BY file_hash
        HAVING COUNT(*) > 1
        LIMIT 1
        """
    ).fetchone()
    if not has_unique_file_hash_index and duplicate_file_hash is None:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash)")
        conn.commit()
    section_columns = {row["name"] for row in conn.execute("PRAGMA table_info(sections)").fetchall()}
    section_column_specs = {
        "document_id": "INTEGER REFERENCES documents(id) ON DELETE CASCADE",
        "parent_id": "INTEGER REFERENCES sections(id)",
        "seq": "INTEGER",
        "title": "TEXT",
        "content": "TEXT",
        "section_type": "TEXT",
    }
    for column, spec in section_column_specs.items():
        if column not in section_columns:
            conn.execute(f"ALTER TABLE sections ADD COLUMN {column} {spec}")
            conn.commit()
            section_columns.add(column)
    translation_columns = {row["name"] for row in conn.execute("PRAGMA table_info(translations)").fetchall()}
    translation_column_specs = {
        "document_id": "INTEGER REFERENCES documents(id) ON DELETE CASCADE",
        "source_lang": "TEXT",
        "target_lang": "TEXT",
        "status": "TEXT DEFAULT 'pending'",
        "output_path": "TEXT",
        "error": "TEXT",
        "created_at": "TEXT",
    }
    for column, spec in translation_column_specs.items():
        if column not in translation_columns:
            conn.execute(f"ALTER TABLE translations ADD COLUMN {column} {spec}")
            conn.commit()
            translation_columns.add(column)
    chunk_columns = {row["name"] for row in conn.execute("PRAGMA table_info(chunks)").fetchall()}
    chunk_column_specs = {
        "document_id": "INTEGER REFERENCES documents(id) ON DELETE CASCADE",
        "section_id": "INTEGER REFERENCES sections(id)",
        "seq": "INTEGER",
        "text": "TEXT",
        "token_count": "INTEGER",
        "vector_id": "TEXT",
        "embedded": "INTEGER DEFAULT 0",
        "created_at": "TEXT",
    }
    for column, spec in chunk_column_specs.items():
        if column not in chunk_columns:
            conn.execute(f"ALTER TABLE chunks ADD COLUMN {column} {spec}")
            conn.commit()
            chunk_columns.add(column)
    reaction_set_columns = {row["name"] for row in conn.execute("PRAGMA table_info(reaction_sets)").fetchall()}
    reaction_set_column_specs = {
        "document_id": "INTEGER REFERENCES documents(id) ON DELETE CASCADE",
        "name": "TEXT",
        "gas_mixture": "TEXT",
        "lxcat_db": "TEXT",
        "source_note": "TEXT",
        "status": "TEXT DEFAULT 'pending'",
        "verified_by": "TEXT",
        "verified_at": "TEXT",
        "created_at": "TEXT",
    }
    for column, spec in reaction_set_column_specs.items():
        if column not in reaction_set_columns:
            conn.execute(f"ALTER TABLE reaction_sets ADD COLUMN {column} {spec}")
            conn.commit()
            reaction_set_columns.add(column)
    reaction_columns = {row["name"] for row in conn.execute("PRAGMA table_info(reactions)").fetchall()}
    reaction_column_specs = {
        "reaction_type": "TEXT",
        "reactants": "TEXT",
        "products": "TEXT",
        "rate_type": "TEXT",
        "rate_value": "TEXT",
        "threshold_ev": "REAL",
        "reference": "TEXT",
        "cross_section_url": "TEXT",
        "source_label": "TEXT",
        "confidence": "REAL",
        "verified": "INTEGER DEFAULT 0",
        "created_at": "TEXT",
    }
    for column, spec in reaction_column_specs.items():
        if column not in reaction_columns:
            conn.execute(f"ALTER TABLE reactions ADD COLUMN {column} {spec}")
            conn.commit()
            reaction_columns.add(column)
    if "source_section_id" not in reaction_columns:
        conn.execute("ALTER TABLE reactions ADD COLUMN source_section_id INTEGER REFERENCES sections(id)")
        conn.commit()
    if "source_excerpt" not in reaction_columns:
        conn.execute("ALTER TABLE reactions ADD COLUMN source_excerpt TEXT")
        conn.commit()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reaction_audits (
            id INTEGER PRIMARY KEY,
            reaction_id INTEGER NOT NULL REFERENCES reactions(id) ON DELETE CASCADE,
            action TEXT NOT NULL,
            changes TEXT,
            verified_by TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    reaction_audit_columns = {row["name"] for row in conn.execute("PRAGMA table_info(reaction_audits)").fetchall()}
    reaction_audit_column_specs = {
        "reaction_id": "INTEGER REFERENCES reactions(id) ON DELETE CASCADE",
        "action": "TEXT",
        "changes": "TEXT",
        "verified_by": "TEXT",
        "created_at": "TEXT",
    }
    for column, spec in reaction_audit_column_specs.items():
        if column not in reaction_audit_columns:
            conn.execute(f"ALTER TABLE reaction_audits ADD COLUMN {column} {spec}")
            conn.commit()
            reaction_audit_columns.add(column)
    ensure_schema_indexes(conn)
    conn.commit()


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_conn() as conn:
        return [dict_from_row(row) for row in conn.execute(sql, params).fetchall()]


def fetch_one(sql: str, params: tuple[Any, ...] = ()) -> Optional[dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict_from_row(row) if row else None
