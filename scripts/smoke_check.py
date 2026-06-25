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
    os.environ["VECTOR_DB_BACKEND"] = "local-json"
    os.environ["PAPER_LAB_SCHEDULER_ENABLED"] = "false"


def assert_ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_status(response, expected: int, label: str) -> dict:
    assert_ok(response.status_code == expected, f"{label}: expected {expected}, got {response.status_code}: {response.text}")
    return response.json()


def assert_error_response(response, expected: int, label: str) -> dict:
    payload = assert_status(response, expected, label)
    error = payload.get("error") if isinstance(payload, dict) else None
    assert_ok(isinstance(error, dict), f"{label}: expected error object, got {payload}")
    assert_ok(isinstance(error.get("code"), str) and error["code"], f"{label}: expected error.code, got {payload}")
    assert_ok(isinstance(error.get("message"), str) and error["message"], f"{label}: expected error.message, got {payload}")
    return payload


def run_smoke() -> dict:
    with tempfile.TemporaryDirectory(prefix="paper-lab-smoke-") as temp:
        base_dir = Path(temp)
        configure_runtime(base_dir)

        from app.config import get_settings
        from app.db import init_db
        from app.fixture_loader import load_fixture_papers
        from app.main import app
        from app.routers import papers as papers_router
        from app.services import crawl as crawl_service
        from fastapi.testclient import TestClient

        get_settings.cache_clear()
        init_db()
        fixture_result = load_fixture_papers()

        client = TestClient(app)
        error_responses = []
        assert_status(client.get("/api/v1/health"), 200, "health")

        papers = assert_status(client.get("/api/v1/papers?q=plasma"), 200, "paper search")
        assert_ok(papers["total"] >= 2, f"expected fixture papers to be searchable, got {papers['total']}")

        original_openalex_client = crawl_service.OpenAlexClient
        original_unpaywall_client = crawl_service.UnpaywallClient

        class OfflineOpenAlexClient:
            def __init__(self, *args, **kwargs):
                pass

            async def works_by_issn(self, issn: str, date_from: str, date_to: str, max_pages: int = 3) -> list[dict]:
                return [
                    {
                        "doi": "10.999/smoke-crawl",
                        "title": "Smoke crawl argon plasma chemistry paper",
                        "abstract": "offline crawl verifies searchable plasma metadata",
                        "authors": [{"name": "Smoke Check", "affiliation": None}],
                        "journal_name": "Plasma Sources Science and Technology",
                        "published_date": "2026-01-15",
                        "published_year": 2026,
                        "landing_url": "https://example.test/smoke-crawl",
                        "source_api": "openalex",
                        "raw_metadata": {"source": "smoke"},
                    },
                    {
                        "doi": "10.999/smoke-filtered",
                        "title": "Unrelated article",
                        "abstract": "no configured keywords here",
                        "authors": [],
                        "journal_name": "Plasma Sources Science and Technology",
                        "published_date": "2026-01-16",
                        "published_year": 2026,
                        "landing_url": "https://example.test/smoke-filtered",
                        "source_api": "openalex",
                        "raw_metadata": {"source": "smoke"},
                    },
                ]

        class OfflineUnpaywallClient:
            def __init__(self, *args, **kwargs):
                pass

            async def resolve(self, doi: str) -> dict:
                return {"oa_status": "green", "oa_pdf_url": f"https://example.test/{doi.replace('/', '-')}.pdf"}

        crawl_service.OpenAlexClient = OfflineOpenAlexClient
        crawl_service.UnpaywallClient = OfflineUnpaywallClient
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
            crawl_service.OpenAlexClient = original_openalex_client
            crawl_service.UnpaywallClient = original_unpaywall_client
        assert_ok(crawl_run["jobs"], "expected crawl run to create a job")
        crawl_job_id = crawl_run["jobs"][0]["job_id"]
        crawl_job = assert_status(client.get(f"/api/v1/crawl/jobs/{crawl_job_id}"), 200, "crawl job detail")
        crawl_diagnostics = crawl_job["diagnostics"]
        assert_ok(crawl_diagnostics["status"] == "success", f"expected crawl job success, got {crawl_diagnostics}")
        assert_ok(crawl_diagnostics["papers_found"] == 2, f"expected crawl papers_found=2, got {crawl_diagnostics}")
        assert_ok(crawl_diagnostics["papers_filtered"] == 1, f"expected crawl papers_filtered=1, got {crawl_diagnostics}")
        assert_ok(crawl_diagnostics["papers_new"] == 1, f"expected crawl papers_new=1, got {crawl_diagnostics}")
        crawled_search = assert_status(client.get("/api/v1/papers?q=smoke crawl"), 200, "crawled paper search")
        assert_ok(crawled_search["total"] >= 1, f"expected crawled paper to be searchable, got {crawled_search}")
        crawled_paper_id = crawled_search["items"][0]["id"]

        original_paper_unpaywall_client = papers_router.UnpaywallClient

        class ManualResolveUnpaywallClient:
            def __init__(self, *args, **kwargs):
                pass

            async def resolve(self, doi: str) -> dict:
                return {
                    "oa_status": "green",
                    "oa_pdf_url": f"https://example.test/manual-resolve-{doi.replace('/', '-')}.pdf",
                    "raw": {"doi": doi, "oa_status": "green", "source": "smoke-manual-resolve"},
                }

        papers_router.UnpaywallClient = ManualResolveUnpaywallClient
        try:
            manual_resolve_oa = assert_status(
                client.post(f"/api/v1/papers/{crawled_paper_id}/resolve-oa"),
                200,
                "manual resolve oa",
            )
        finally:
            papers_router.UnpaywallClient = original_paper_unpaywall_client
        assert_ok(
            manual_resolve_oa["oa_status"] == "green",
            f"expected manual resolve oa_status=green, got {manual_resolve_oa}",
        )
        assert_ok(
            manual_resolve_oa.get("oa_pdf_url", "").startswith("https://example.test/manual-resolve-"),
            f"expected manual resolve oa_pdf_url, got {manual_resolve_oa}",
        )

        smoke_pdf = (
            b"%PDF-1.4\nArgon plasma chemistry and electron impact reactions. "
            b"The rate is $k_1$. LXCat IST-Lisbon https://nl.lxcat.net/data/set/example "
            b"e + Ar -> e + e + Ar+ ."
        )
        upload = assert_status(
            client.post(
                "/api/v1/documents",
                files={"file": ("smoke.pdf", smoke_pdf, "application/pdf")},
            ),
            201,
            "document upload",
        )
        document_id = upload["id"]
        duplicate_upload = client.post(
            "/api/v1/documents",
            files={"file": ("smoke-copy.pdf", smoke_pdf, "application/pdf")},
        )
        duplicate_payload = assert_error_response(duplicate_upload, 409, "duplicate document upload")
        error_responses.append(duplicate_payload["error"]["code"])
        duplicate_document = duplicate_payload["document"]
        assert_ok(
            duplicate_document["id"] == document_id,
            f"expected duplicate document id {document_id}, got {duplicate_document}",
        )

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
        rag_answer_has_citation = (
            "Source:" in (rag.get("answer") or "")
            and ("paper_id=" in (rag.get("answer") or "") or "document_id=" in (rag.get("answer") or ""))
            and "chunk_id=" in (rag.get("answer") or "")
        )
        rag_source_excerpts = len([source for source in rag["sources"] if source.get("source_excerpt")])
        assert_ok(rag_answer_has_citation, f"expected RAG answer citation, got {rag.get('answer')!r}")
        assert_ok(rag_source_excerpts == len(rag["sources"]), f"expected source excerpts in RAG sources, got {rag['sources']}")

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
        blocked_payload = assert_error_response(blocked_export, 409, "unverified reaction export")
        error_responses.append(blocked_payload["error"]["code"])
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
        verified_export_payload = json.loads(Path(verified_export["output_path"]).read_text(encoding="utf-8"))
        exported_reactions = verified_export_payload.get("reactions") or []
        assert_ok(len(exported_reactions) == 1, f"expected one reaction in JSON export, got {exported_reactions}")
        export_audit_entries = [
            audit
            for reaction in exported_reactions
            for audit in reaction.get("audit_log") or []
        ]
        assert_ok(
            any(audit.get("verified_by") == "smoke-check" for audit in export_audit_entries),
            f"expected smoke-check audit entry in JSON export, got {export_audit_entries}",
        )
        export_source_sections = [
            reaction.get("source_section_id")
            for reaction in exported_reactions
            if reaction.get("source_section_id")
            and reaction.get("source_section_title")
            and reaction.get("source_section_type")
            and reaction.get("source_section_seq") is not None
        ]
        assert_ok(export_source_sections, f"expected source section fields in JSON export, got {exported_reactions}")
        txt_export = assert_status(
            client.post(f"/api/v1/reaction-sets/{reaction_set_id}/export?format=txt"),
            200,
            "verified reaction txt export",
        )
        bolsig_export = assert_status(
            client.post(f"/api/v1/reaction-sets/{reaction_set_id}/export?format=bolsig"),
            200,
            "verified reaction bolsig export",
        )
        txt_path = Path(txt_export["output_path"])
        bolsig_path = Path(bolsig_export["output_path"])
        assert_ok(txt_path.exists(), "expected verified txt export file")
        assert_ok(bolsig_path.exists(), "expected verified bolsig export file")
        txt_content = txt_path.read_text(encoding="utf-8")
        bolsig_content = bolsig_path.read_text(encoding="utf-8")
        txt_contains_reaction = "e + Ar -> e + e + Ar+" in txt_content and "rate: original source value" in txt_content
        txt_has_source_excerpt = "source_excerpt:" in txt_content and "e + Ar -> e + e + Ar+ ." in txt_content
        bolsig_contains_header = (
            "# BOLSIG+ / LXCat compatible reaction summary" in bolsig_content
            and "PROCESS 1" in bolsig_content
            and "REACTION: e + Ar -> e + e + Ar+" in bolsig_content
        )
        txt_has_verification_metadata = "verified_by: smoke-check" in txt_content and "verified_at:" in txt_content
        bolsig_has_verification_metadata = "# VERIFIED_BY: smoke-check" in bolsig_content and "# VERIFIED_AT:" in bolsig_content
        txt_has_confidence = "confidence: " in txt_content
        bolsig_has_confidence = "CONFIDENCE: " in bolsig_content
        txt_has_source_label = "source_label: " in txt_content
        bolsig_has_source_label = "SOURCE_LABEL: " in bolsig_content
        assert_ok(txt_contains_reaction, f"expected reaction and rate in txt export, got {txt_content!r}")
        assert_ok(txt_has_source_excerpt, f"expected source excerpt in txt export, got {txt_content!r}")
        assert_ok(bolsig_contains_header, f"expected BOLSIG header and reaction, got {bolsig_content!r}")
        assert_ok(txt_has_verification_metadata, f"expected verification metadata in txt export, got {txt_content!r}")
        assert_ok(
            bolsig_has_verification_metadata,
            f"expected verification metadata in BOLSIG export, got {bolsig_content!r}",
        )
        assert_ok(txt_has_confidence, f"expected confidence in txt export, got {txt_content!r}")
        assert_ok(bolsig_has_confidence, f"expected confidence in BOLSIG export, got {bolsig_content!r}")
        assert_ok(txt_has_source_label, f"expected source_label in txt export, got {txt_content!r}")
        assert_ok(bolsig_has_source_label, f"expected SOURCE_LABEL in BOLSIG export, got {bolsig_content!r}")

        status = assert_status(client.get("/api/v1/system/status"), 200, "system status")
        runtime = status["runtime"]
        config_warnings = status["config_warnings"]
        assert_ok(runtime["version"], "expected runtime version")
        scheduler_job_ids = [job["id"] for job in runtime.get("scheduler_jobs") or []]
        assert_ok(
            scheduler_job_ids == ["crawl-daily", "crawl-weekly", "crawl-monthly"],
            f"expected scheduler crawl jobs, got {scheduler_job_ids}",
        )
        assert_ok(isinstance(config_warnings, list), "expected config_warnings list")
        counts = status["counts"]
        status_counts = status["status_counts"]
        release_readiness = status["release_readiness"]
        assert_ok(status_counts["crawl_jobs"]["success"] == 1, "expected successful crawl job count")
        assert_ok(status_counts["document_parse"]["parsed"] == 1, "expected parsed document count")
        assert_ok(status_counts["document_index"]["indexed"] == 1, "expected indexed document count")
        assert_ok(status_counts["document_chemistry"]["extracted"] == 1, "expected extracted chemistry count")
        assert_ok(status_counts["translations"]["done"] == 1, "expected done translation count")
        assert_ok(status_counts["reaction_sets"]["verified"] == 1, "expected verified reaction set count")
        assert_ok(release_readiness["ready"] is False, "expected smoke release readiness to be blocked by config warnings")
        assert_ok(release_readiness["demo_data_missing"] == [], "expected smoke demo data to satisfy readiness")
        assert_ok(release_readiness["failed_workflows"] == [], "expected smoke readiness to have no failed workflows")
        assert_ok(release_readiness["storage_errors"] == [], "expected smoke readiness to have writable storage")
        assert_ok(counts["papers"] >= 2, "expected system status to include fixture papers")
        assert_ok("paper_categories" in counts, "expected paper category count")
        assert_ok(counts["documents"] == 1, "expected one smoke document")
        assert_ok(counts["sections"] >= 1, "expected parsed section count")
        assert_ok(counts["chunks"] >= 1, "expected indexed chunk count")
        assert_ok(counts["translations"] == 1, "expected one translation")
        assert_ok(counts["reaction_sets"] == 1, "expected one reaction set")
        assert_ok(counts["reactions"] == 1, "expected one reaction")
        assert_ok(counts["reaction_audits"] >= 1, "expected reaction audit count")

        return {
            "fixture": fixture_result,
            "papers": papers["total"],
            "paper_categories": counts["paper_categories"],
            "status_counts": status_counts,
            "release_readiness": release_readiness,
            "crawl_jobs": counts["crawl_jobs"],
            "crawl_job_status": crawl_diagnostics["status"],
            "crawl_job_found": crawl_diagnostics["papers_found"],
            "crawl_job_filtered": crawl_diagnostics["papers_filtered"],
            "crawl_job_new": crawl_diagnostics["papers_new"],
            "crawled_papers": crawled_search["total"],
            "manual_resolve_oa_status": manual_resolve_oa["oa_status"],
            "manual_resolve_oa_pdf_url": manual_resolve_oa["oa_pdf_url"],
            "document_id": document_id,
            "duplicate_upload_status": duplicate_upload.status_code,
            "duplicate_document_id": duplicate_document["id"],
            "error_response_count": len(error_responses),
            "error_response_codes": error_responses,
            "sections": counts["sections"],
            "chunks": counts["chunks"],
            "rag_sources": len(rag["sources"]),
            "rag_answer_has_citation": rag_answer_has_citation,
            "rag_source_excerpts": rag_source_excerpts,
            "translation_status": translation["status"],
            "translation_output_path": translation["output_path"],
            "reaction_sets": counts["reaction_sets"],
            "reactions": counts["reactions"],
            "reaction_audits": counts["reaction_audits"],
            "blocked_export_status": blocked_export.status_code,
            "verified_export_format": verified_export["format"],
            "verified_export_formats": [verified_export["format"], txt_export["format"], bolsig_export["format"]],
            "verified_export_path": verified_export["output_path"],
            "verified_export_response_reactions": verified_export["reaction_count"],
            "verified_export_response_audit_entries": verified_export["audit_entry_count"],
            "verified_export_reactions": len(exported_reactions),
            "verified_export_audit_entries": len(export_audit_entries),
            "verified_export_source_sections": len(export_source_sections),
            "verified_export_text_files": len([txt_export["output_path"], bolsig_export["output_path"]]),
            "verified_export_bolsig_contains_header": bolsig_contains_header,
            "verified_export_txt_contains_reaction": txt_contains_reaction,
            "verified_export_txt_has_source_excerpt": txt_has_source_excerpt,
            "verified_export_txt_has_verification_metadata": txt_has_verification_metadata,
            "verified_export_bolsig_has_verification_metadata": bolsig_has_verification_metadata,
            "verified_export_txt_has_confidence": txt_has_confidence,
            "verified_export_bolsig_has_confidence": bolsig_has_confidence,
            "verified_export_txt_has_source_label": txt_has_source_label,
            "verified_export_bolsig_has_source_label": bolsig_has_source_label,
            "runtime_version": runtime["version"],
            "scheduler_job_ids": scheduler_job_ids,
            "config_warning_count": len(config_warnings),
        }


def main() -> int:
    result = run_smoke()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
