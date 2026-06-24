#!/usr/bin/env python3
import json
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
        from app.db import get_conn, init_db
        from app.fixture_loader import load_fixture_papers
        from app.main import app
        from app.routers import crawl as crawl_router
        from app.utils import now_iso
        from fastapi.testclient import TestClient

        get_settings.cache_clear()
        init_db()
        fixture_result = load_fixture_papers()

        client = TestClient(app)
        assert_status(client.get("/api/v1/health"), 200, "health")

        papers = assert_status(client.get("/api/v1/papers?q=plasma"), 200, "paper search")
        assert_ok(papers["total"] >= 2, f"expected fixture papers to be searchable, got {papers['total']}")

        original_crawl_runner = crawl_router.run_crawl_job

        async def offline_crawl_runner(job_id: int, journal_id: int, date_from: str, date_to: str) -> None:
            with get_conn() as conn:
                conn.execute(
                    """
                    UPDATE crawl_jobs
                    SET status='success',
                        started_at=?,
                        finished_at=?,
                        papers_found=2,
                        papers_filtered=1,
                        papers_new=0,
                        error=NULL
                    WHERE id=?
                    """,
                    (now_iso(), now_iso(), job_id),
                )

        crawl_router.run_crawl_job = offline_crawl_runner
        try:
            crawl_run = assert_status(
                client.post(
                    "/api/v1/crawl/run",
                    json={
                        "journal_ids": [2],
                        "period": "manual",
                        "date_from": "2026-01-01",
                        "date_to": "2026-01-31",
                    },
                ),
                202,
                "crawl run",
            )
        finally:
            crawl_router.run_crawl_job = original_crawl_runner
        assert_ok(crawl_run["jobs"], "expected crawl run to create a job")
        crawl_job_id = crawl_run["jobs"][0]["job_id"]
        crawl_job = assert_status(client.get(f"/api/v1/crawl/jobs/{crawl_job_id}"), 200, "crawl job detail")
        crawl_diagnostics = crawl_job["diagnostics"]
        assert_ok(crawl_diagnostics["status"] == "success", f"expected crawl job success, got {crawl_diagnostics}")
        assert_ok(crawl_diagnostics["papers_found"] == 2, f"expected crawl papers_found=2, got {crawl_diagnostics}")
        assert_ok(crawl_diagnostics["papers_filtered"] == 1, f"expected crawl papers_filtered=1, got {crawl_diagnostics}")

        upload = assert_status(
            client.post(
                "/api/v1/documents",
                files={
                    "file": (
                        "smoke.pdf",
                        (
                            b"%PDF-1.4\nArgon plasma chemistry and electron impact reactions. "
                            b"The rate is $k_1$. LXCat IST-Lisbon https://nl.lxcat.net/data/set/example "
                            b"e + Ar -> e + e + Ar+ ."
                        ),
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

        assert_status(
            client.post(f"/api/v1/documents/{document_id}/translate", json={"target_lang": "zh"}),
            202,
            "document translate",
        )
        translation = assert_status(
            client.get(f"/api/v1/documents/{document_id}/translation"),
            200,
            "document translation",
        )
        assert_ok(translation["status"] == "done", f"expected translation done, got {translation['status']}")
        assert_ok(Path(translation["output_path"]).exists(), "expected translation output file")

        rag = assert_status(
            client.post(
                "/api/v1/rag/query",
                json={"question": "electron impact chemistry", "document_ids": [document_id], "top_k": 2},
            ),
            200,
            "rag query",
        )
        assert_ok(bool(rag["sources"]), "expected RAG sources")

        assert_status(
            client.post(f"/api/v1/documents/{document_id}/extract-chemistry"),
            202,
            "chemistry extraction",
        )
        reaction_sets = assert_status(
            client.get(f"/api/v1/documents/{document_id}/reaction-sets"),
            200,
            "document reaction sets",
        )
        assert_ok(reaction_sets["total"] == 1, f"expected one reaction set, got {reaction_sets['total']}")
        reaction_set_id = reaction_sets["items"][0]["id"]
        reaction_detail = assert_status(
            client.get(f"/api/v1/reaction-sets/{reaction_set_id}"),
            200,
            "reaction set detail",
        )
        assert_ok(len(reaction_detail["reactions"]) == 1, "expected one extracted reaction")
        reaction_id = reaction_detail["reactions"][0]["id"]
        blocked_export = client.post(f"/api/v1/reaction-sets/{reaction_set_id}/export?format=json")
        assert_ok(
            blocked_export.status_code == 409,
            f"expected unverified export gate, got {blocked_export.status_code}: {blocked_export.text}",
        )
        verified = assert_status(
            client.put(
                f"/api/v1/reactions/{reaction_id}/verify",
                json={
                    "verified": True,
                    "reaction_type": "ionization",
                    "rate_type": "cross_section",
                    "rate_value": "original source value",
                    "threshold_ev": 15.76,
                    "cross_section_url": "https://nl.lxcat.net/data/set/example",
                    "verified_by": "smoke-check",
                },
            ),
            200,
            "reaction verify",
        )
        assert_ok(verified["status"] == "verified", f"expected verified reaction set, got {verified['status']}")
        verified_export = assert_status(
            client.post(f"/api/v1/reaction-sets/{reaction_set_id}/export?format=json"),
            200,
            "verified reaction export",
        )
        assert_ok(Path(verified_export["output_path"]).exists(), "expected verified export file")

        status = assert_status(client.get("/api/v1/system/status"), 200, "system status")
        runtime = status["runtime"]
        config_warnings = status["config_warnings"]
        assert_ok(runtime["version"], "expected runtime version")
        assert_ok(isinstance(config_warnings, list), "expected config_warnings list")
        counts = status["counts"]
        assert_ok(counts["papers"] >= 2, "expected system status to include fixture papers")
        assert_ok(counts["documents"] == 1, "expected one smoke document")
        assert_ok(counts["sections"] >= 1, "expected parsed section count")
        assert_ok(counts["chunks"] >= 1, "expected indexed chunk count")
        assert_ok(counts["translations"] == 1, "expected one translation")
        assert_ok(counts["reaction_sets"] == 1, "expected one reaction set")
        assert_ok(counts["reactions"] == 1, "expected one reaction")

        return {
            "fixture": fixture_result,
            "papers": papers["total"],
            "crawl_jobs": counts["crawl_jobs"],
            "crawl_job_status": crawl_diagnostics["status"],
            "crawl_job_found": crawl_diagnostics["papers_found"],
            "crawl_job_filtered": crawl_diagnostics["papers_filtered"],
            "crawl_job_new": crawl_diagnostics["papers_new"],
            "document_id": document_id,
            "sections": counts["sections"],
            "chunks": counts["chunks"],
            "rag_sources": len(rag["sources"]),
            "translation_status": translation["status"],
            "translation_output_path": translation["output_path"],
            "reaction_sets": counts["reaction_sets"],
            "reactions": counts["reactions"],
            "blocked_export_status": blocked_export.status_code,
            "verified_export_format": verified_export["format"],
            "verified_export_path": verified_export["output_path"],
            "runtime_version": runtime["version"],
            "config_warning_count": len(config_warnings),
        }


def main() -> int:
    result = run_smoke()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
