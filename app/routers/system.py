import json
import os
from pathlib import Path

from fastapi import APIRouter

from app import __version__
from app.clients.grobid import GrobidClient
from app.config import get_settings
from app.db import fetch_one, get_conn
from app.scheduler import scheduled_crawl_jobs
from app.services.rag import SUPPORTED_EMBEDDING_MODELS, SUPPORTED_VECTOR_DB_BACKENDS

router = APIRouter(prefix="/system", tags=["system"])


def normalize_grobid_status(detail: dict, fallback_url: str) -> dict:
    return {
        "url": detail.get("url") or fallback_url,
        "available": detail.get("available"),
        "status_code": detail.get("status_code"),
        "error": detail.get("error"),
    }


def table_count(table: str) -> int:
    row = fetch_one(f"SELECT COUNT(*) AS n FROM {table}") or {"n": 0}
    return row["n"]


def status_count(table: str, column: str) -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT COALESCE({column}, 'unknown') AS status, COUNT(*) AS n
            FROM {table}
            GROUP BY COALESCE({column}, 'unknown')
            ORDER BY status
            """
        ).fetchall()
    return {row["status"]: row["n"] for row in rows}


def storage_path_health(path: Path) -> dict:
    exists = path.exists()
    return {
        "path": str(path),
        "exists": exists,
        "writable": bool(exists and os.access(path, os.W_OK)),
    }


def vector_store_health(path: Path) -> dict:
    exists = path.exists()
    readable = bool(exists and os.access(path, os.R_OK))
    health = {
        "path": str(path),
        "exists": exists,
        "readable": readable,
        "writable": bool(exists and os.access(path, os.W_OK)),
        "valid_json": None,
        "error": None,
    }
    if not exists:
        return health
    if not readable:
        health["valid_json"] = False
        health["error"] = "vector store is not readable"
        return health
    try:
        json.loads(path.read_text(encoding="utf-8"))
        health["valid_json"] = True
    except Exception as exc:
        health["valid_json"] = False
        health["error"] = str(exc)
    return health


def storage_health(settings) -> dict:
    return {
        "data_dir": storage_path_health(settings.data_dir),
        "pdf_dir": storage_path_health(settings.pdf_dir),
        "tei_dir": storage_path_health(settings.tei_dir),
        "translation_dir": storage_path_health(settings.translation_dir),
        "export_dir": storage_path_health(settings.export_dir),
        "database": storage_path_health(settings.database_path),
        "database_parent": storage_path_health(settings.database_path.parent),
        "vector_db_parent": storage_path_health(settings.vector_db_path.parent),
        "vector_db": vector_store_health(settings.vector_db_path),
    }


def config_warnings(settings) -> list[dict]:
    warnings = []
    if not settings.openalex_mailto:
        warnings.append(
            {
                "code": "missing_openalex_mailto",
                "capability": "openalex_crawl",
                "message": "OPENALEX_MAILTO is not configured; local offline mode still works, but production crawl diagnostics are weaker.",
            }
        )
    if not settings.unpaywall_email:
        warnings.append(
            {
                "code": "missing_unpaywall_email",
                "capability": "oa_lookup",
                "message": "UNPAYWALL_EMAIL is not configured; OA link enrichment may fail against the public API.",
            }
        )
    if not settings.llm_api_key:
        warnings.append(
            {
                "code": "missing_llm_api_key",
                "capability": "llm_translation",
                "message": "LLM_API_KEY is not configured; translation uses the local deterministic adapter.",
            }
        )
    if (settings.embedding_model or "").strip().lower() not in SUPPORTED_EMBEDDING_MODELS:
        warnings.append(
            {
                "code": "unsupported_embedding_model",
                "capability": "rag_indexing",
                "message": f"EMBEDDING_MODEL={settings.embedding_model} is not supported by the local adapter registry.",
            }
        )
    if (settings.vector_db_backend or "").strip().lower() not in SUPPORTED_VECTOR_DB_BACKENDS:
        warnings.append(
            {
                "code": "unsupported_vector_db_backend",
                "capability": "rag_indexing",
                "message": f"VECTOR_DB_BACKEND={settings.vector_db_backend} is not supported by the current vector store registry.",
            }
        )
    return warnings


@router.get("/status")
async def status(check_external: bool = False) -> dict:
    settings = get_settings()
    grobid = normalize_grobid_status({}, settings.grobid_url)
    if check_external:
        grobid = normalize_grobid_status(await GrobidClient(settings.grobid_url).health_detail(), settings.grobid_url)
    return {
        "database_path": str(settings.database_path),
        "runtime": {
            "api_prefix": settings.api_prefix,
            "scheduler_enabled": settings.scheduler_enabled,
            "scheduler_jobs": scheduled_crawl_jobs(),
            "version": __version__,
        },
        "config_warnings": config_warnings(settings),
        "storage": {
            "data_dir": str(settings.data_dir),
            "pdf_dir": str(settings.pdf_dir),
            "tei_dir": str(settings.tei_dir),
            "translation_dir": str(settings.translation_dir),
            "export_dir": str(settings.export_dir),
            "vector_db_path": str(settings.vector_db_path),
        },
        "storage_health": storage_health(settings),
        "external_capabilities": {
            "openalex_mailto": bool(settings.openalex_mailto),
            "unpaywall_email": bool(settings.unpaywall_email),
            "grobid_url": settings.grobid_url,
            "grobid": grobid,
            "llm_api_key": bool(settings.llm_api_key),
            "embedding_model": settings.embedding_model,
            "vector_db_backend": settings.vector_db_backend,
        },
        "status_counts": {
            "crawl_jobs": status_count("crawl_jobs", "status"),
            "document_parse": status_count("documents", "parse_status"),
            "document_index": status_count("documents", "index_status"),
            "document_chemistry": status_count("documents", "chemistry_status"),
            "translations": status_count("translations", "status"),
            "reaction_sets": status_count("reaction_sets", "status"),
        },
        "counts": {
            "journals": table_count("journals"),
            "papers": table_count("papers"),
            "categories": table_count("categories"),
            "paper_categories": table_count("paper_categories"),
            "crawl_jobs": table_count("crawl_jobs"),
            "documents": table_count("documents"),
            "sections": table_count("sections"),
            "translations": table_count("translations"),
            "chunks": table_count("chunks"),
            "reaction_sets": table_count("reaction_sets"),
            "reactions": table_count("reactions"),
            "reaction_audits": table_count("reaction_audits"),
        },
    }
