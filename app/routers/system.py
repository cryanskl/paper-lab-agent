from fastapi import APIRouter

from app.config import get_settings
from app.db import fetch_one

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status")
def status() -> dict:
    settings = get_settings()
    journal_count = fetch_one("SELECT COUNT(*) AS n FROM journals") or {"n": 0}
    paper_count = fetch_one("SELECT COUNT(*) AS n FROM papers") or {"n": 0}
    document_count = fetch_one("SELECT COUNT(*) AS n FROM documents") or {"n": 0}
    return {
        "database_path": str(settings.database_path),
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
            "llm_api_key": bool(settings.llm_api_key),
            "embedding_model": settings.embedding_model,
        },
        "counts": {
            "journals": journal_count["n"],
            "papers": paper_count["n"],
            "documents": document_count["n"],
        },
    }

