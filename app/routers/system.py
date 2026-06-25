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

DEMO_DATA_MIN_COUNTS = {
    "journals": 6,
    "papers": 1,
    "documents": 1,
    "sections": 1,
    "chunks": 1,
    "reaction_sets": 1,
    "reactions": 1,
}

RELEASE_STORAGE_WRITABLE_KEYS = [
    "data_dir",
    "pdf_dir",
    "tei_dir",
    "translation_dir",
    "export_dir",
    "database_parent",
    "vector_db_parent",
]


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


def demo_data_status(counts: dict[str, int]) -> dict:
    missing = [
        f"{key}>={minimum}"
        for key, minimum in DEMO_DATA_MIN_COUNTS.items()
        if counts.get(key, 0) < minimum
    ]
    return {
        "ready": not missing,
        "requirements": DEMO_DATA_MIN_COUNTS,
        "missing": missing,
        "counts": {key: counts.get(key, 0) for key in DEMO_DATA_MIN_COUNTS},
    }


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


def storage_readiness_errors(health: dict) -> list[str]:
    errors = []
    for key in RELEASE_STORAGE_WRITABLE_KEYS:
        entry = health.get(key)
        if not isinstance(entry, dict):
            errors.append(key)
            continue
        if entry.get("exists") is not True:
            errors.append(f"{key}.exists")
        if entry.get("writable") is not True:
            errors.append(f"{key}.writable")

    database = health.get("database")
    if isinstance(database, dict) and database.get("exists") is True and database.get("writable") is not True:
        errors.append("database.writable")

    vector_db = health.get("vector_db")
    if isinstance(vector_db, dict) and vector_db.get("exists") is True and vector_db.get("writable") is not True:
        errors.append("vector_db.writable")
    if isinstance(vector_db, dict) and vector_db.get("exists") is True and vector_db.get("valid_json") is not True:
        errors.append("vector_db.valid_json")

    return errors


def failed_workflow_errors(status_counts: dict) -> list[str]:
    errors = []
    for workflow, counts in status_counts.items():
        if not isinstance(counts, dict):
            continue
        failed = counts.get("failed")
        if isinstance(failed, int) and not isinstance(failed, bool) and failed > 0:
            errors.append(f"{workflow}.failed={failed}")
    return errors


def warning_codes(warnings: list[dict]) -> list[str]:
    return [
        warning["code"].strip()
        for warning in warnings
        if isinstance(warning, dict) and isinstance(warning.get("code"), str) and warning["code"].strip()
    ]


def release_readiness_status(
    demo_data: dict,
    warnings: list[dict],
    health: dict,
    status_counts: dict,
) -> dict:
    demo_data_missing = [str(item) for item in demo_data.get("missing", []) if str(item).strip()]
    failed_workflows = failed_workflow_errors(status_counts)
    config_warning_codes = warning_codes(warnings)
    storage_errors = storage_readiness_errors(health)
    return {
        "ready": not (demo_data_missing or failed_workflows or config_warning_codes or storage_errors),
        "demo_data_missing": demo_data_missing,
        "failed_workflows": failed_workflows,
        "config_warning_codes": config_warning_codes,
        "storage_errors": storage_errors,
    }


@router.get("/status")
async def status(check_external: bool = False) -> dict:
    settings = get_settings()
    grobid = normalize_grobid_status({}, settings.grobid_url)
    if check_external:
        grobid = normalize_grobid_status(await GrobidClient(settings.grobid_url).health_detail(), settings.grobid_url)
    counts = {
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
    }
    warnings = config_warnings(settings)
    health = storage_health(settings)
    status_counts = {
        "crawl_jobs": status_count("crawl_jobs", "status"),
        "document_parse": status_count("documents", "parse_status"),
        "document_index": status_count("documents", "index_status"),
        "document_chemistry": status_count("documents", "chemistry_status"),
        "translations": status_count("translations", "status"),
        "reaction_sets": status_count("reaction_sets", "status"),
    }
    demo_data = demo_data_status(counts)
    return {
        "database_path": str(settings.database_path),
        "runtime": {
            "api_prefix": settings.api_prefix,
            "scheduler_enabled": settings.scheduler_enabled,
            "scheduler_jobs": scheduled_crawl_jobs(),
            "version": __version__,
        },
        "config_warnings": warnings,
        "storage": {
            "data_dir": str(settings.data_dir),
            "pdf_dir": str(settings.pdf_dir),
            "tei_dir": str(settings.tei_dir),
            "translation_dir": str(settings.translation_dir),
            "export_dir": str(settings.export_dir),
            "vector_db_path": str(settings.vector_db_path),
        },
        "storage_health": health,
        "external_capabilities": {
            "openalex_mailto": bool(settings.openalex_mailto),
            "unpaywall_email": bool(settings.unpaywall_email),
            "grobid_url": settings.grobid_url,
            "grobid": grobid,
            "llm_api_key": bool(settings.llm_api_key),
            "translation_adapter": "openai-compatible" if settings.llm_api_key else "local-echo",
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
            "vector_db_backend": settings.vector_db_backend,
        },
        "status_counts": status_counts,
        "counts": counts,
        "demo_data": demo_data,
        "release_readiness": release_readiness_status(demo_data, warnings, health, status_counts),
    }
