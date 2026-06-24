#!/usr/bin/env python3
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def configure_runtime(base_dir: Path) -> None:
    os.environ["DATABASE_PATH"] = str(base_dir / "plasma.db")
    os.environ["PAPER_LAB_DATA_DIR"] = str(base_dir)
    os.environ["PAPER_LAB_PDF_DIR"] = str(base_dir / "pdfs")
    os.environ["PAPER_LAB_TEI_DIR"] = str(base_dir / "tei")
    os.environ["PAPER_LAB_TRANSLATION_DIR"] = str(base_dir / "translations")
    os.environ["PAPER_LAB_EXPORT_DIR"] = str(base_dir / "exports")
    os.environ["VECTOR_DB_PATH"] = str(base_dir / "vector-index.json")
    os.environ["PAPER_LAB_SCHEDULER_ENABLED"] = "false"


def assert_ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_status(response, expected: int, label: str) -> dict:
    assert_ok(response.status_code == expected, f"{label}: expected {expected}, got {response.status_code}: {response.text}")
    return response.json()


def run_smoke() -> dict:
    with tempfile.TemporaryDirectory(prefix="paper-lab-smoke-") as temp:
        base_dir = Path(temp)
        configure_runtime(base_dir)

        from app.config import get_settings
        from app.db import init_db
        from app.fixture_loader import load_fixture_papers
        from app.main import app
        from fastapi.testclient import TestClient

        get_settings.cache_clear()
        init_db()
        fixture_result = load_fixture_papers()

        client = TestClient(app)
        assert_status(client.get("/api/v1/health"), 200, "health")

        papers = assert_status(client.get("/api/v1/papers?q=plasma"), 200, "paper search")
        assert_ok(papers["total"] >= 2, f"expected fixture papers to be searchable, got {papers['total']}")

        upload = assert_status(
            client.post(
                "/api/v1/documents",
                files={
                    "file": (
                        "smoke.pdf",
                        b"%PDF-1.4\nArgon plasma chemistry and electron impact reactions. The rate is $k_1$.",
                        "application/pdf",
                    )
                },
            ),
            201,
            "document upload",
        )
        document_id = upload["id"]

        assert_status(client.post(f"/api/v1/documents/{document_id}/parse"), 202, "document parse")
        sections = assert_status(client.get(f"/api/v1/documents/{document_id}/sections"), 200, "document sections")
        assert_ok(sections["total"] >= 1, "expected parsed document sections")

        assert_status(client.post(f"/api/v1/documents/{document_id}/index"), 202, "document index")
        chunks = assert_status(client.get(f"/api/v1/documents/{document_id}/chunks"), 200, "document chunks")
        assert_ok(chunks["total"] >= 1, "expected indexed document chunks")

        rag = assert_status(
            client.post(
                "/api/v1/rag/query",
                json={"question": "electron impact chemistry", "document_ids": [document_id], "top_k": 2},
            ),
            200,
            "rag query",
        )
        assert_ok(bool(rag["sources"]), "expected RAG sources")

        status = assert_status(client.get("/api/v1/system/status"), 200, "system status")
        counts = status["counts"]
        assert_ok(counts["papers"] >= 2, "expected system status to include fixture papers")
        assert_ok(counts["documents"] == 1, "expected one smoke document")
        assert_ok(counts["sections"] >= 1, "expected parsed section count")
        assert_ok(counts["chunks"] >= 1, "expected indexed chunk count")

        return {
            "fixture": fixture_result,
            "papers": papers["total"],
            "document_id": document_id,
            "sections": counts["sections"],
            "chunks": counts["chunks"],
            "rag_sources": len(rag["sources"]),
        }


def main() -> int:
    result = run_smoke()
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
