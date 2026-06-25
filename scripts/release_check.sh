#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${PYTHON:-}" ]]; then
  PYTHON_CMD=("${PYTHON}")
elif [[ -x ".venv/bin/python" ]]; then
  PYTHON_CMD=(".venv/bin/python")
elif command -v uv >/dev/null 2>&1; then
  PYTHON_CMD=("uv" "run" "python")
else
  PYTHON_CMD=("python")
fi

bash -n scripts/env.sh
bash -n scripts/dev.sh
"${PYTHON_CMD[@]}" -m py_compile scripts/health_check.py scripts/import_fixtures.py scripts/prepare_demo_data.py scripts/smoke_check.py scripts/validate_api_contract.py scripts/validate_bug_docs.py scripts/validate_docs_links.py scripts/validate_env_example.py scripts/validate_readme_commands.py scripts/validate_release_hygiene.py scripts/validate_requirements.py scripts/validate_schema.py streamlit_app.py
"${PYTHON_CMD[@]}" scripts/health_check.py --help >/dev/null
"${PYTHON_CMD[@]}" scripts/prepare_demo_data.py --help >/dev/null
"${PYTHON_CMD[@]}" scripts/validate_api_contract.py
"${PYTHON_CMD[@]}" scripts/validate_bug_docs.py
"${PYTHON_CMD[@]}" scripts/validate_docs_links.py
"${PYTHON_CMD[@]}" scripts/validate_env_example.py
"${PYTHON_CMD[@]}" scripts/validate_readme_commands.py
"${PYTHON_CMD[@]}" scripts/validate_release_hygiene.py
"${PYTHON_CMD[@]}" scripts/validate_requirements.py
"${PYTHON_CMD[@]}" scripts/validate_schema.py
FIXTURE_JSON="$("${PYTHON_CMD[@]}" - <<'PY'
import json
import os
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory(prefix="paper-lab-fixtures-") as fixture_dir:
    env = os.environ.copy()
    env["PAPER_LAB_DATA_DIR"] = fixture_dir
    for key in [
        "DATABASE_PATH",
        "PAPER_LAB_PDF_DIR",
        "PAPER_LAB_TEI_DIR",
        "PAPER_LAB_TRANSLATION_DIR",
        "PAPER_LAB_EXPORT_DIR",
        "VECTOR_DB_PATH",
        "VECTOR_DB_BACKEND",
    ]:
        env.pop(key, None)
    result = subprocess.run(
        [sys.executable, "scripts/import_fixtures.py"],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
payload = json.loads(result.stdout)
expected = {
    ("papers", "inserted"): 2,
    ("documents", "inserted"): 1,
}
for (section, key), value in expected.items():
    actual = payload.get(section, {}).get(key)
    if actual != value:
        print(f"release_check failed: fixture {section}.{key}={actual!r}, expected {value!r}", file=sys.stderr)
        raise SystemExit(1)
print(json.dumps(payload, ensure_ascii=False))
PY
)"
printf '%s\n' "${FIXTURE_JSON}"
PREPARE_DEMO_JSON="$("${PYTHON_CMD[@]}" - <<'PY'
import json
import os
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory(prefix="paper-lab-demo-") as demo_dir:
    env = os.environ.copy()
    env["PAPER_LAB_DATA_DIR"] = demo_dir
    for key in [
        "DATABASE_PATH",
        "PAPER_LAB_PDF_DIR",
        "PAPER_LAB_TEI_DIR",
        "PAPER_LAB_TRANSLATION_DIR",
        "PAPER_LAB_EXPORT_DIR",
        "VECTOR_DB_PATH",
        "VECTOR_DB_BACKEND",
    ]:
        env.pop(key, None)
    # Validate the release demo path directly: scripts/prepare_demo_data.py --compact.
    result = subprocess.run(
        [sys.executable, "scripts/prepare_demo_data.py", "--compact"],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    payload = json.loads(result.stdout)
    # Validate the compact release summary path directly: scripts/prepare_demo_data.py --summary-only --compact.
    summary_result = subprocess.run(
        [sys.executable, "scripts/prepare_demo_data.py", "--summary-only", "--compact"],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    summary_payload = json.loads(summary_result.stdout)
    for name, export_payload in payload.get("exports", {}).items():
        path = export_payload.get("output_path")
        if not path or not os.path.exists(path):
            print(f"release_check failed: prepare_demo_data export {name} missing at {path!r}", file=sys.stderr)
            raise SystemExit(1)
if payload.get("demo_data", {}).get("ready") is not True:
    print(
        f"release_check failed: prepare_demo_data demo_data.ready={payload.get('demo_data', {}).get('ready')!r}, "
        f"missing={payload.get('demo_data', {}).get('missing')!r}",
        file=sys.stderr,
    )
    raise SystemExit(1)
summary = payload.get("summary") or {}
if summary.get("ready") is not True:
    print(
        f"release_check failed: prepare_demo_data summary.ready={summary.get('ready')!r}, "
        f"missing={summary.get('missing')!r}",
        file=sys.stderr,
    )
    raise SystemExit(1)
if summary_payload != summary:
    print("release_check failed: prepare_demo_data --summary-only output does not match payload.summary", file=sys.stderr)
    raise SystemExit(1)
if any(key in summary_payload for key in ("document", "exports")):
    print("release_check failed: prepare_demo_data --summary-only leaked full payload keys", file=sys.stderr)
    raise SystemExit(1)
expected_counts = {
    "papers": 2,
    "documents": 1,
    "sections": 1,
    "chunks": 1,
    "translations": 1,
    "reaction_sets": 1,
    "reactions": 1,
    "reaction_audits": 1,
}
for key, minimum in expected_counts.items():
    actual = payload.get("counts", {}).get(key)
    if not isinstance(actual, int) or isinstance(actual, bool) or actual < minimum:
        print(f"release_check failed: prepare_demo_data counts.{key}={actual!r}, expected >= {minimum}", file=sys.stderr)
        raise SystemExit(1)
expected_export_formats = ["json", "txt", "bolsig"]
if sorted(payload.get("exports", {})) != sorted(expected_export_formats):
    print(
        f"release_check failed: prepare_demo_data exports={sorted(payload.get('exports', {}))!r}, "
        f"expected {expected_export_formats!r}",
        file=sys.stderr,
    )
    raise SystemExit(1)
if summary.get("export_formats") != expected_export_formats:
    print(
        f"release_check failed: prepare_demo_data summary.export_formats={summary.get('export_formats')!r}, "
        f"expected {expected_export_formats!r}",
        file=sys.stderr,
    )
    raise SystemExit(1)
if payload.get("reaction_set", {}).get("status") != "verified":
    print(f"release_check failed: prepare_demo_data reaction_set.status={payload.get('reaction_set', {}).get('status')!r}, expected 'verified'", file=sys.stderr)
    raise SystemExit(1)
if summary.get("reaction_set_status") != "verified":
    print(f"release_check failed: prepare_demo_data summary.reaction_set_status={summary.get('reaction_set_status')!r}, expected 'verified'", file=sys.stderr)
    raise SystemExit(1)
print(json.dumps(payload, ensure_ascii=False))
PY
)"
printf '%s\n' "${PREPARE_DEMO_JSON}"
SMOKE_JSON="$("${PYTHON_CMD[@]}" -m scripts.smoke_check)"
printf '%s\n' "${SMOKE_JSON}"
SMOKE_JSON="${SMOKE_JSON}" "${PYTHON_CMD[@]}" - <<'PY'
import json
import os
import sys

from app import __version__

payload = json.loads(os.environ["SMOKE_JSON"])
expected = {
    "crawl_job_status": "success",
    "translation_status": "done",
    "blocked_export_status": 409,
    "verified_export_format": "json",
    "verified_export_formats": ["json", "txt", "bolsig"],
    "runtime_version": __version__,
    "scheduler_job_ids": ["crawl-daily", "crawl-weekly", "crawl-monthly"],
    "config_warning_count": 3,
    "document_detail_has_paper": True,
    "document_detail_parse_status": "uploaded",
    "document_list_total": 1,
    "duplicate_upload_status": 409,
    "error_response_count": 2,
    "auto_classify_category_count": 1,
    "auto_classify_method": "auto",
    "journal_filter_search_hits": 1,
    "crawl_job_list_total": 1,
    "crawl_job_detail_status": "success",
    "crawl_job_detail_journal_name": "Plasma Sources Science and Technology",
    "crawl_job_detail_diagnostics_outcome": "new_papers",
    "crawl_job_detail_diagnostics_papers_accepted": 1,
    "manual_category_count": 1,
    "manual_category_method": "manual",
    "manual_category_search_hits": 1,
    "manual_resolve_oa_status": "green",
    "manual_resolve_oa_pdf_url": "https://example.test/manual-resolve-10.999-smoke-crawl.pdf",
    "oa_only_search_hits": 1,
    "paper_detail_doi": "10.999/smoke-crawl",
    "paper_detail_has_raw_metadata": True,
    "papers": 2,
    "paper_categories": 1,
    "relevance_sort_search_hits": 1,
    "year_filter_search_hits": 1,
    "sections": 1,
    "section_list_first_type": "body",
    "section_list_has_content": True,
    "chunks": 1,
    "chunk_list_index_status": "indexed",
    "chunk_list_has_vector_id": True,
    "chunk_list_has_section_title": True,
    "rag_sources": 1,
    "reaction_sets": 1,
    "reactions": 1,
    "verified_export_reactions": 1,
    "verified_export_response_reactions": 1,
    "verified_export_response_audit_entries": 1,
    "verified_export_source_sections": 1,
    "verified_export_text_files": 2,
    "verified_export_bolsig_contains_header": True,
    "verified_export_txt_contains_reaction": True,
    "verified_export_txt_has_source_excerpt": True,
    "rag_answer_has_citation": True,
    "rag_source_excerpts": 1,
    "verified_export_txt_has_verification_metadata": True,
    "verified_export_bolsig_has_verification_metadata": True,
    "verified_export_txt_has_confidence": True,
    "verified_export_bolsig_has_confidence": True,
    "verified_export_txt_has_source_label": True,
    "verified_export_bolsig_has_source_label": True,
}
for key, value in expected.items():
    if payload.get(key) != value:
        print(f"release_check failed: smoke {key}={payload.get(key)!r}, expected {value!r}", file=sys.stderr)
        raise SystemExit(1)
if not payload.get("verified_export_path"):
    print("release_check failed: smoke verified_export_path is missing", file=sys.stderr)
    raise SystemExit(1)
if payload.get("crawl_job_found", 0) < 1:
    print(f"release_check failed: smoke crawl_job_found={payload.get('crawl_job_found')!r}, expected >= 1", file=sys.stderr)
    raise SystemExit(1)
if payload.get("crawl_job_new", 0) < 1:
    print(f"release_check failed: smoke crawl_job_new={payload.get('crawl_job_new')!r}, expected >= 1", file=sys.stderr)
    raise SystemExit(1)
if payload.get("crawled_papers", 0) < 1:
    print(f"release_check failed: smoke crawled_papers={payload.get('crawled_papers')!r}, expected >= 1", file=sys.stderr)
    raise SystemExit(1)
if "paper_categories" not in payload:
    print("release_check failed: smoke paper_categories is missing", file=sys.stderr)
    raise SystemExit(1)
release_readiness = payload.get("release_readiness")
if not isinstance(release_readiness, dict):
    print("release_check failed: smoke release_readiness is missing", file=sys.stderr)
    raise SystemExit(1)
expected_readiness = {
    "ready": False,
    "demo_data_missing": [],
    "failed_workflows": [],
    "config_warning_codes": ["missing_openalex_mailto", "missing_unpaywall_email", "missing_llm_api_key"],
    "storage_errors": [],
}
for key, value in expected_readiness.items():
    if release_readiness.get(key) != value:
        print(
            f"release_check failed: smoke release_readiness.{key}={release_readiness.get(key)!r}, expected {value!r}",
            file=sys.stderr,
        )
        raise SystemExit(1)
status_counts = payload.get("status_counts")
if not isinstance(status_counts, dict):
    print("release_check failed: smoke status_counts is missing", file=sys.stderr)
    raise SystemExit(1)
failed_statuses = []
for section, counts in status_counts.items():
    if isinstance(counts, dict):
        failed = counts.get("failed")
        if isinstance(failed, int) and not isinstance(failed, bool) and failed > 0:
            failed_statuses.append(f"{section}.failed={failed}")
if failed_statuses:
    print(f"release_check failed: smoke failed statuses present ({'; '.join(failed_statuses)})", file=sys.stderr)
    raise SystemExit(1)
expected_status_counts = {
    ("crawl_jobs", "success"): 1,
    ("document_parse", "parsed"): 1,
    ("document_index", "indexed"): 1,
    ("document_chemistry", "extracted"): 1,
    ("translations", "done"): 1,
    ("reaction_sets", "verified"): 1,
}
for (section, state), value in expected_status_counts.items():
    actual = status_counts.get(section, {}).get(state)
    if actual != value:
        print(
            f"release_check failed: smoke status_counts.{section}.{state}={actual!r}, expected {value!r}",
            file=sys.stderr,
        )
        raise SystemExit(1)
if not payload.get("duplicate_document_id"):
    print("release_check failed: smoke duplicate_document_id is missing", file=sys.stderr)
    raise SystemExit(1)
if payload.get("verified_export_audit_entries", 0) < 1:
    print(
        f"release_check failed: smoke verified_export_audit_entries={payload.get('verified_export_audit_entries')!r}, expected >= 1",
        file=sys.stderr,
    )
    raise SystemExit(1)
if payload.get("reaction_audits", 0) < 1:
    print(
        f"release_check failed: smoke reaction_audits={payload.get('reaction_audits')!r}, expected >= 1",
        file=sys.stderr,
    )
    raise SystemExit(1)
PY
"${PYTHON_CMD[@]}" -m pytest -q
