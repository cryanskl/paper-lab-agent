# Release Checklist

Use this checklist before publishing, demoing, or handing off `paper-lab-agent`.

## 1. Local Gate

Run the same offline release gate used by CI:

```bash
python scripts/doctor.py --strict --compact
bash scripts/release_check.sh
```

The strict preflight doctor checks Python version, required project files, and importable Python dependencies before service startup, and exits non-zero when any required check fails. The release gate validates shell syntax, Python compilation, API/schema/docs/env/requirement hygiene, the unified dev startup path, fixture import, demo data preparation, smoke coverage, and the full test suite.

## 2. Demo Data

Prepare and inspect walking skeleton data:

```bash
python scripts/prepare_demo_data.py --summary-only --compact
```

The compact summary should report `ready: true`, parsed/indexed/extracted/done statuses, a verified reaction set, and `json`, `txt`, `bolsig` export formats.

## 3. API Contract Handoff

Export the current OpenAPI schema for frontend handoff, review, or release artifacts:

```bash
python scripts/export_openapi.py --output out/openapi.json
```

The output is generated under `out/`, which is ignored by Git. Do not hand-edit the exported schema; regenerate it from the app.

## 4. Live Runtime

After starting the app with `bash scripts/dev.sh`, run:

```bash
python scripts/health_check.py --require-release-ready
python scripts/health_check.py --require-frontend
python scripts/health_check.py --require-openapi
```

`--require-release-ready` checks storage writability, no failed workflow backlog, no config warnings, and demo data readiness. `--require-frontend` verifies the Streamlit health endpoint. `--require-openapi` verifies the live `/openapi.json` schema used by frontend handoff.

## 5. Optional External Gate

For real PDF parsing deployments with GROBID running:

```bash
python scripts/health_check.py --require-grobid
```

This gate is intentionally separate because local fallback mode and offline CI do not require GROBID.

## 6. GitHub Gate

GitHub Actions runs `.github/workflows/ci.yml` on push and pull request. It also exposes `workflow_dispatch`, so the release gate can be triggered manually before a demo or release handoff.

## 7. Git Safety

Before tagging, publishing, or handing off a release, confirm that the checkout matches the intended branch and worktree:

```bash
git branch --show-current
git rev-parse --show-toplevel
git status --short
git diff --check
```

`git status --short` should be empty. If it prints anything, review whether those changes belong to this release before publishing.
