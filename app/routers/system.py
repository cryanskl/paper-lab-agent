from fastapi import APIRouter

from app.clients.grobid import GrobidClient
from app.config import get_settings
from app.db import fetch_one

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
        "external_capabilities": {
            "openalex_mailto": bool(settings.openalex_mailto),
            "unpaywall_email": bool(settings.unpaywall_email),
            "grobid_url": settings.grobid_url,
            "grobid": grobid,
            "llm_api_key": bool(settings.llm_api_key),
            "embedding_model": settings.embedding_model,
        },
        "counts": {
            "journals": table_count("journals"),
            "papers": table_count("papers"),
            "categories": table_count("categories"),
            "crawl_jobs": table_count("crawl_jobs"),
            "documents": table_count("documents"),
            "sections": table_count("sections"),
            "translations": table_count("translations"),
            "chunks": table_count("chunks"),
            "reaction_sets": table_count("reaction_sets"),
            "reactions": table_count("reactions"),
        },
    }
