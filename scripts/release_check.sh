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
git diff --check
git diff --cached --check
"${PYTHON_CMD[@]}" -m compileall -q app scripts tests streamlit_app.py
"${PYTHON_CMD[@]}" -m py_compile scripts/doctor.py scripts/export_openapi.py scripts/export_release_artifacts.py scripts/health_check.py scripts/import_fixtures.py scripts/package_release_artifacts.py scripts/prepare_demo_data.py scripts/smoke_check.py scripts/validate_api_contract.py scripts/validate_bug_docs.py scripts/validate_docs_links.py scripts/validate_env_example.py scripts/validate_readme_commands.py scripts/validate_release_artifacts.py scripts/validate_release_hygiene.py scripts/validate_release_package.py scripts/validate_requirements.py scripts/validate_schema.py streamlit_app.py
"${PYTHON_CMD[@]}" scripts/doctor.py --help >/dev/null
"${PYTHON_CMD[@]}" scripts/doctor.py --strict --compact
"${PYTHON_CMD[@]}" scripts/export_openapi.py --help >/dev/null
"${PYTHON_CMD[@]}" scripts/export_release_artifacts.py --help >/dev/null
"${PYTHON_CMD[@]}" scripts/health_check.py --help >/dev/null
"${PYTHON_CMD[@]}" scripts/package_release_artifacts.py --help >/dev/null
"${PYTHON_CMD[@]}" scripts/prepare_demo_data.py --help >/dev/null
"${PYTHON_CMD[@]}" scripts/validate_release_artifacts.py --help >/dev/null
"${PYTHON_CMD[@]}" scripts/validate_release_package.py --help >/dev/null
"${PYTHON_CMD[@]}" scripts/validate_api_contract.py
"${PYTHON_CMD[@]}" scripts/validate_bug_docs.py
"${PYTHON_CMD[@]}" scripts/validate_docs_links.py
"${PYTHON_CMD[@]}" scripts/validate_env_example.py
"${PYTHON_CMD[@]}" scripts/validate_readme_commands.py
"${PYTHON_CMD[@]}" scripts/validate_release_hygiene.py
"${PYTHON_CMD[@]}" scripts/validate_requirements.py
"${PYTHON_CMD[@]}" scripts/validate_schema.py
OPENAPI_JSON="$(mktemp)"
"${PYTHON_CMD[@]}" scripts/export_openapi.py --output "${OPENAPI_JSON}" --compact
OPENAPI_JSON="${OPENAPI_JSON}" "${PYTHON_CMD[@]}" - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads(Path(os.environ["OPENAPI_JSON"]).read_text(encoding="utf-8"))
tag_names = {tag.get("name") for tag in payload.get("tags", [])}
if payload.get("info", {}).get("title") != "paper-lab-agent":
    raise SystemExit("release_check failed: OpenAPI title mismatch")
if "/api/v1/health" not in payload.get("paths", {}):
    raise SystemExit("release_check failed: OpenAPI missing /api/v1/health")
if "system" not in tag_names:
    raise SystemExit("release_check failed: OpenAPI missing system tag metadata")
if "ErrorResponse" not in payload.get("components", {}).get("schemas", {}):
    raise SystemExit("release_check failed: OpenAPI missing ErrorResponse schema")
PY
rm -f "${OPENAPI_JSON}"
DEV_CHECK_JSON="$("${PYTHON_CMD[@]}" - <<'PY'
import json
import os
import socket
import subprocess
import sys
import tempfile


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


with tempfile.TemporaryDirectory(prefix="paper-lab-dev-") as data_dir:
    api_port = free_port()
    streamlit_port = free_port()
    env = os.environ.copy()
    env.update(
        {
            "PYTHON": sys.executable,
            "PAPER_LAB_DATA_DIR": data_dir,
            "API_PORT": str(api_port),
            "STREAMLIT_PORT": str(streamlit_port),
            "DEV_READY_TIMEOUT": "30",
            "DEV_EXIT_AFTER_READY": "true",
            "PAPER_LAB_SCHEDULER_ENABLED": "false",
        }
    )
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
        ["bash", "scripts/dev.sh"],
        text=True,
        capture_output=True,
        timeout=45,
        check=True,
        env=env,
    )
expected = {
    "fastapi": f"FastAPI:   http://127.0.0.1:{api_port}",
    "streamlit": f"Streamlit: http://127.0.0.1:{streamlit_port}",
    "api_base_url": f"API_BASE_URL=http://127.0.0.1:{api_port}/api/v1",
    "exit_after_ready": "DEV_EXIT_AFTER_READY=true",
}
missing = [value for value in expected.values() if value not in result.stdout]
if missing:
    print(
        f"release_check failed: dev.sh output missing {missing!r}; stdout={result.stdout!r}; stderr={result.stderr!r}",
        file=sys.stderr,
    )
    raise SystemExit(1)
print(json.dumps({"dev_script_ready": True, "api_port": api_port, "streamlit_port": streamlit_port}))
PY
)"
printf '%s\n' "${DEV_CHECK_JSON}"
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
from datetime import datetime


def stable_prepare_demo_summary(summary):
    return {key: value for key, value in summary.items() if key != "reaction_set_verified_at"}


def validate_prepare_demo_summary_reviewer(summary, label):
    if summary.get("reaction_set_verified_by") != "prepare-demo-data":
        print(
            f"release_check failed: prepare_demo_data {label}.reaction_set_verified_by="
            f"{summary.get('reaction_set_verified_by')!r}, expected 'prepare-demo-data'",
            file=sys.stderr,
        )
        raise SystemExit(1)
    verified_at = summary.get("reaction_set_verified_at")
    if not isinstance(verified_at, str) or not verified_at.strip():
        print(
            f"release_check failed: prepare_demo_data {label}.reaction_set_verified_at={verified_at!r}, "
            "expected ISO8601 timestamp",
            file=sys.stderr,
        )
        raise SystemExit(1)
    try:
        datetime.fromisoformat(verified_at.strip().replace("Z", "+00:00"))
    except ValueError:
        print(
            f"release_check failed: prepare_demo_data {label}.reaction_set_verified_at={verified_at!r}, "
            "expected ISO8601 timestamp",
            file=sys.stderr,
        )
        raise SystemExit(1)

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
    summary_output_path = os.path.join(demo_dir, "out", "demo-summary.json")
    summary_output_result = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_demo_data.py",
            "--summary-only",
            "--compact",
            "--output",
            summary_output_path,
        ],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    if summary_output_result.stdout:
        print("release_check failed: prepare_demo_data --output should not write JSON to stdout", file=sys.stderr)
        raise SystemExit(1)
    summary_output_payload = json.loads(open(summary_output_path, encoding="utf-8").read())
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
validate_prepare_demo_summary_reviewer(summary, "payload.summary")
validate_prepare_demo_summary_reviewer(summary_payload, "--summary-only output")
validate_prepare_demo_summary_reviewer(summary_output_payload, "--output summary")
if stable_prepare_demo_summary(summary_payload) != stable_prepare_demo_summary(summary):
    print("release_check failed: prepare_demo_data --summary-only output does not match payload.summary", file=sys.stderr)
    raise SystemExit(1)
if stable_prepare_demo_summary(summary_output_payload) != stable_prepare_demo_summary(summary):
    print("release_check failed: prepare_demo_data --output summary does not match payload.summary", file=sys.stderr)
    raise SystemExit(1)
if any(key in summary_payload for key in ("document", "exports")):
    print("release_check failed: prepare_demo_data --summary-only leaked full payload keys", file=sys.stderr)
    raise SystemExit(1)
if any(key in summary_output_payload for key in ("document", "exports")):
    print("release_check failed: prepare_demo_data --output summary leaked full payload keys", file=sys.stderr)
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
RELEASE_ARTIFACTS_JSON="$("${PYTHON_CMD[@]}" - <<'PY'
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory(prefix="paper-lab-release-") as release_dir:
    env = os.environ.copy()
    env["PAPER_LAB_DATA_DIR"] = os.path.join(release_dir, "data")
    output_dir = Path(release_dir) / "out" / "release"
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
        [
            sys.executable,
            "scripts/export_release_artifacts.py",
            "--output-dir",
            str(output_dir),
            "--compact",
        ],
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    manifest = json.loads(result.stdout)
    manifest_path = output_dir / "release-manifest.json"
    demo_summary_path = output_dir / "demo-summary.json"
    openapi_path = output_dir / "openapi.json"
    file_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    demo_summary = json.loads(demo_summary_path.read_text(encoding="utf-8"))
    openapi = json.loads(openapi_path.read_text(encoding="utf-8"))
    if manifest != file_manifest:
        print("release_check failed: release-manifest.json differs from stdout manifest", file=sys.stderr)
        raise SystemExit(1)
    if manifest.get("service") != "paper-lab-agent":
        print(f"release_check failed: release manifest service={manifest.get('service')!r}", file=sys.stderr)
        raise SystemExit(1)
    if manifest.get("version") != openapi.get("info", {}).get("version"):
        print("release_check failed: release manifest version does not match OpenAPI version", file=sys.stderr)
        raise SystemExit(1)
    if manifest.get("artifacts") != {
        "openapi": "openapi.json",
        "demo_summary": "demo-summary.json",
        "manifest": "release-manifest.json",
    }:
        print(f"release_check failed: release manifest artifacts={manifest.get('artifacts')!r}", file=sys.stderr)
        raise SystemExit(1)
    if manifest.get("demo_ready") is not True or demo_summary.get("ready") is not True:
        print("release_check failed: release handoff demo summary is not ready", file=sys.stderr)
        raise SystemExit(1)
    if manifest.get("demo_export_formats") != ["json", "txt", "bolsig"]:
        print(f"release_check failed: release manifest demo_export_formats={manifest.get('demo_export_formats')!r}", file=sys.stderr)
        raise SystemExit(1)
    if (
        manifest.get("demo_reaction_set_verified_by") != "prepare-demo-data"
        or not manifest.get("demo_reaction_set_verified_at")
    ):
        print(f"release_check failed: release manifest demo reviewer metadata={manifest!r}", file=sys.stderr)
        raise SystemExit(1)
    if "/api/v1/health" not in openapi.get("paths", {}):
        print("release_check failed: release handoff OpenAPI missing /api/v1/health", file=sys.stderr)
        raise SystemExit(1)
    validate_result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_release_artifacts.py",
            "--artifact-dir",
            str(output_dir),
            "--compact",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    validation = json.loads(validate_result.stdout)
    if validation.get("ok") is not True:
        print(f"release_check failed: release artifact validation={validation!r}", file=sys.stderr)
        raise SystemExit(1)
    source = validation.get("source") or {}
    if not source.get("git_commit") or not source.get("git_branch"):
        print(f"release_check failed: release artifact source={source!r}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(source.get("git_dirty"), bool):
        print(f"release_check failed: release artifact source.git_dirty={source.get('git_dirty')!r}", file=sys.stderr)
        raise SystemExit(1)
    checksums = validation.get("checksums") or {}
    if sorted(checksums) != ["demo-summary.json", "openapi.json", "release-manifest.json"]:
        print(f"release_check failed: release artifact checksums={checksums!r}", file=sys.stderr)
        raise SystemExit(1)
    package_path = Path(release_dir) / "out" / "paper-lab-agent-release.zip"
    package_result = subprocess.run(
        [
            sys.executable,
            "scripts/package_release_artifacts.py",
            "--artifact-dir",
            str(output_dir),
            "--output",
            str(package_path),
            "--compact",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    package = json.loads(package_result.stdout)
    if (
        package.get("ok") is not True
        or package.get("artifact_count") != 3
        or package.get("artifact_names") != ["demo-summary.json", "openapi.json", "release-manifest.json"]
        or package.get("demo_ready") is not True
        or package.get("demo_export_formats") != ["json", "txt", "bolsig"]
        or package.get("demo_export_audit_entry_counts") != {"json": 1, "txt": 1, "bolsig": 1}
        or package.get("demo_reaction_set_verified_by") != "prepare-demo-data"
        or not package.get("demo_reaction_set_verified_at")
        or not package_path.exists()
    ):
        print(f"release_check failed: release artifact package={package!r}", file=sys.stderr)
        raise SystemExit(1)
    validate_package_result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_release_package.py",
            "--package",
            str(package_path),
            "--compact",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    package_validation = json.loads(validate_package_result.stdout)
    if (
        package_validation.get("ok") is not True
        or package_validation.get("artifact_count") != 3
        or package_validation.get("artifact_names") != ["demo-summary.json", "openapi.json", "release-manifest.json"]
        or package_validation.get("demo_ready") is not True
        or package_validation.get("demo_export_formats") != ["json", "txt", "bolsig"]
        or package_validation.get("demo_export_audit_entry_counts") != {"json": 1, "txt": 1, "bolsig": 1}
        or package_validation.get("demo_reaction_set_verified_by") != "prepare-demo-data"
        or not package_validation.get("demo_reaction_set_verified_at")
    ):
        print(f"release_check failed: release package validation={package_validation!r}", file=sys.stderr)
        raise SystemExit(1)
print(json.dumps(package, ensure_ascii=False))
PY
)"
printf '%s\n' "${RELEASE_ARTIFACTS_JSON}"
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
    "unsupported_export_status": 400,
    "verified_export_format": "json",
    "verified_export_formats": ["json", "txt", "bolsig"],
    "runtime_version": __version__,
    "scheduler_job_ids": ["crawl-daily", "crawl-weekly", "crawl-monthly"],
    "config_warning_count": 3,
    "system_translation_adapter": "local-echo",
    "system_embedding_model": "local-hash",
    "system_vector_db_backend": "local-json",
    "system_grobid_url": "http://127.0.0.1:8070",
    "system_storage_data_dir_writable": True,
    "system_storage_database_parent_writable": True,
    "system_storage_vector_db_exists": True,
    "system_storage_vector_db_valid_json": True,
    "document_detail_has_paper": True,
    "document_detail_parse_status": "uploaded",
    "document_list_total": 1,
    "duplicate_document_matches_original": True,
    "duplicate_upload_status": 409,
    "unsupported_document_status": 415,
    "error_response_count": 4,
    "auto_classify_category_count": 1,
    "auto_classify_method": "auto",
    "journal_filter_search_hits": 1,
    "crawl_job_found": 4,
    "crawl_job_new": 2,
    "crawl_job_list_total": 1,
    "crawl_job_detail_status": "success",
    "crawl_job_detail_journal_name": "Plasma Sources Science and Technology",
    "crawl_job_detail_diagnostics_outcome": "new_papers",
    "crawl_job_detail_diagnostics_papers_accepted": 3,
    "crawl_job_detail_keyword_mode": "or",
    "crawl_job_detail_has_keyword_terms": True,
    "crawl_job_detail_keyword_terms_include_plasma_chemistry": True,
    "no_doi_search_hits": 1,
    "no_doi_paper_has_doi": False,
    "no_doi_paper_dedupe_strategy": "no_doi_fingerprint",
    "no_doi_paper_has_dedupe_key": True,
    "manual_category_count": 1,
    "manual_category_method": "manual",
    "manual_category_search_hits": 1,
    "manual_resolve_oa_status": "green",
    "manual_resolve_oa_pdf_url": "https://example.test/manual-resolve-10.999-smoke-crawl.pdf",
    "oa_only_search_hits": 1,
    "paper_detail_doi": "10.999/smoke-crawl",
    "paper_detail_has_raw_metadata": True,
    "papers": 2,
    "paper_categories": 2,
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
    "verified_export_reaction_type": "ionization",
    "verified_export_rate_type": "cross_section",
    "verified_export_text_files": 2,
    "verified_export_bolsig_contains_header": True,
    "verified_export_txt_contains_reaction": True,
    "verified_export_txt_has_source_excerpt": True,
    "rag_answer_has_citation": True,
    "rag_source_excerpts": 1,
    "rag_source_has_document_id": True,
    "rag_source_has_paper_id": True,
    "rag_source_has_section_id": True,
    "rag_source_has_section_title": True,
    "rag_source_has_section_type": True,
    "rag_source_has_chunk_id": True,
    "rag_source_has_vector_id": True,
    "rag_source_has_score": True,
    "document_reaction_set_list_total": 1,
    "document_reaction_set_reaction_count": 1,
    "document_reaction_set_verified_count_before_verify": 0,
    "document_reaction_set_unverified_count_before_verify": 1,
    "document_reaction_set_export_ready_before_verify": False,
    "document_reaction_set_export_ready_after_verify": True,
    "reaction_set_detail_reaction_count_before_verify": 1,
    "reaction_set_detail_verified_count_before_verify": 0,
    "reaction_set_detail_unverified_count_before_verify": 1,
    "reaction_set_detail_export_ready_before_verify": False,
    "extracted_reaction_type": "ionization",
    "extracted_rate_type": "cross_section",
    "reaction_set_detail_export_ready_after_verify": True,
    "reaction_set_detail_audit_entries_after_verify": 1,
    "verified_export_has_smoke_check_audit": True,
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
expected_error_codes = {
    "document_duplicate",
    "reaction_set_unverified",
    "unsupported_document_type",
    "unsupported_export_format",
}
actual_error_codes = set(payload.get("error_response_codes") or [])
missing_error_codes = sorted(expected_error_codes - actual_error_codes)
if missing_error_codes:
    print(
        f"release_check failed: smoke error_response_codes missing {missing_error_codes!r}; "
        f"actual={sorted(actual_error_codes)!r}",
        file=sys.stderr,
    )
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
    "ready": True,
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
