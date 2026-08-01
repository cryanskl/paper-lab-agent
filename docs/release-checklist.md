# Release Checklist

Use this checklist before publishing, demoing, or handing off `paper-lab-agent`.

For PRD-to-release coverage, use the [Release Acceptance Matrix](release-acceptance-matrix.md) alongside this checklist.

## 1. Local Gate

Run the same production-index release gate used by CI:

```bash
python scripts/doctor.py --strict --compact
bash scripts/release_check.sh
```

The strict preflight doctor checks Python version, required project files, importable Python dependencies, whether local storage paths are creatable and writable, and external capability configuration warnings before service startup. It reads `.env` for local path configuration while preserving exported environment variable overrides. Compact output includes `warning_count`, `warning_codes`, and `warning_details` for optional OpenAlex, Unpaywall, and LLM configuration gaps, plus RAG adapter warnings such as `unsupported_embedding_model` and `unsupported_vector_db_backend`. The release gate validates the production `bge-m3 + Chroma` index contract and no longer switches to the legacy hash index. It also validates shell syntax, Python compilation, every Python script under the scripts directory with `--help` to catch CLI argument and import path failures, API/schema/docs/env/requirement hygiene, the unified dev startup path, fixture import, demo data preparation, a live API with prepared demo data, smoke coverage, and the full test suite.

The API contract gate compares `docs/接口设计文档.md` with the generated OpenAPI schema and fails on missing, undocumented, or duplicate documented routes.

## 2. Demo Data

Prepare and inspect walking skeleton data:

```bash
python scripts/prepare_demo_data.py --summary-only --compact
python scripts/prepare_demo_data.py --summary-only --compact --output out/demo-summary.json
```

The compact summary should report `ready: true`, parsed/indexed/extracted/done statuses, a verified reaction set, `json`, `txt`, `bolsig` export formats, positive `export_audit_entry_counts` for each export format, and `export_audit_summary_formats` covering all three export formats. Use `--output out/demo-summary.json` when you need a handoff artifact alongside the OpenAPI export.

## 3. API Contract Handoff

Export the current OpenAPI schema for frontend handoff, review, or release artifacts:

```bash
python scripts/build_release_handoff.py --artifact-dir out/release --package out/paper-lab-agent-release.zip --compact
python scripts/export_openapi.py --output out/openapi.json
python scripts/export_release_artifacts.py --output-dir out/release --compact
python scripts/validate_release_artifacts.py --artifact-dir out/release --compact
python scripts/package_release_artifacts.py --artifact-dir out/release --output out/paper-lab-agent-release.zip --compact
python scripts/validate_release_package.py --package out/paper-lab-agent-release.zip --compact
```

Use `scripts/build_release_handoff.py` for the normal handoff path: it runs export, validate, package, validate package in order and returns the final package validation report with the completed stage map. Keep the individual commands for debugging a specific stage.

The combined release artifact command writes `openapi.json`, `demo-summary.json`, `release-acceptance-matrix.md`, and `release-manifest.json` into the target directory. The manifest records source git commit/branch, source dirty state, artifact count, artifact names, OpenAPI path count, demo resource counts, demo workflow statuses, demo export audit counts, demo export audit summary formats, doctor preflight state, `preflight_warning_codes`, `preflight_warning_details`, and file checksums. Validate the directory before handoff so a non-directory artifact path, missing files, unreadable artifact paths, unexpected extra files, checksum mismatches, edited summaries, edited acceptance matrices, an acceptance matrix that no longer matches the source `docs/release-acceptance-matrix.md` byte-for-byte, manifest artifact count drift, manifest artifact names drift, manifest/summary count drift, manifest/summary workflow status drift, manifest/summary audit count drift, manifest/summary audit summary drift, preflight evidence drift, version drift, malformed manifests, missing OpenAPI `system` tag metadata, or missing `ErrorResponse` schema fail before sharing. Package the validated directory when you need a single handoff file; the package report includes resolved `artifact_dir`, resolved `package_path`, `artifact_count`, `artifact_names`, `source`, lowercase hex SHA256 `package_sha256`, `service`, `version`, `openapi_path_count`, lowercase hex SHA256 `checksums`, demo readiness, `demo_counts`, `demo_workflow_statuses`, export formats, `demo_export_audit_entry_counts`, `demo_export_audit_summary_formats`, `reaction_set_verified_by`, `reaction_set_verified_at`, `preflight_warning_codes`, and `preflight_warning_details`. Keep the zip output outside the artifact directory so packaging cannot overwrite or pollute the handoff files. Then validate the zip so the package can be unpacked and rechecked before delivery; package validation rejects unsafe archive names, symlink artifacts, and non-file artifact entries before extraction. The package validation report exposes the same demo and preflight evidence and must report the same `source`, `package_sha256`, and `checksums`. For final handoff after committing, add `--require-clean-source` to validation or packaging to fail if the manifest was exported from a dirty worktree. The output is generated under `out/`, which is ignored by Git. Do not hand-edit the exported schema, summary, or acceptance matrix; regenerate them from the app.

## 4. Live Runtime

After starting the app with `bash scripts/dev.sh`, run:

```bash
python scripts/health_check.py --summary-only --compact
python scripts/health_check.py --require-release-ready
python scripts/health_check.py --require-frontend
python scripts/health_check.py --require-openapi
```

Use the compact summary first to inspect `release_ready` and `release_blockers`, then run the required gates to fail fast. Also inspect `storage_health` before handoff: `database_parent` confirms SQLite can be created or updated, and `vector_db_parent` confirms first-run vector index creation can write to the configured parent directory even when the vector index file does not exist yet.
Inspect `config_warnings` when release readiness is blocked by configuration: unsupported RAG adapter warnings include `actual` and `supported`, so the current configured adapter and the supported values can be compared without reading source code.
`--require-release-ready` checks storage writability, no failed, rejected, or unknown workflow backlog, and demo data readiness. Use `--require-no-config-warnings` separately when the handoff requires OpenAlex, Unpaywall, or LLM configuration. `--require-frontend` verifies the native workbench page. `--require-openapi` verifies the live `/openapi.json` schema used by frontend handoff.

## 5. Optional External Gate

For real PDF parsing deployments with GROBID running:

```bash
python scripts/health_check.py --require-grobid
```

This gate is intentionally separate because fixture-based CI does not require a live GROBID service.

## 6. GitHub Gate

GitHub Actions runs `.github/workflows/ci.yml` on push and pull request. It also exposes `workflow_dispatch`, so the release gate can be triggered manually before a demo or release handoff.

## 7. Git Safety

Before tagging, publishing, or handing off a release, confirm that the checkout matches the intended branch and worktree:

```bash
git branch --show-current
git rev-parse --show-toplevel
git status --short
git diff --check
git diff --cached --check
```

`git status --short` should be empty. If it prints anything, review whether those changes belong to this release before publishing. The two diff checks cover both unstaged and staged whitespace or conflict-marker errors.
