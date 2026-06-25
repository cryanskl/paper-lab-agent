# Release Checklist

Use this checklist before publishing, demoing, or handing off `paper-lab-agent`.

## 1. Local Gate

Run the same offline release gate used by CI:

```bash
bash scripts/release_check.sh
```

This validates shell syntax, Python compilation, API/schema/docs/env/requirement hygiene, the unified dev startup path, fixture import, demo data preparation, smoke coverage, and the full test suite.

## 2. Demo Data

Prepare and inspect walking skeleton data:

```bash
python scripts/prepare_demo_data.py --summary-only --compact
```

The compact summary should report `ready: true`, parsed/indexed/extracted/done statuses, a verified reaction set, and `json`, `txt`, `bolsig` export formats.

## 3. Live Runtime

After starting the app with `bash scripts/dev.sh`, run:

```bash
python scripts/health_check.py --require-release-ready
python scripts/health_check.py --require-frontend
```

`--require-release-ready` checks storage writability, no failed workflow backlog, no config warnings, and demo data readiness. `--require-frontend` verifies the Streamlit health endpoint.

## 4. Optional External Gate

For real PDF parsing deployments with GROBID running:

```bash
python scripts/health_check.py --require-grobid
```

This gate is intentionally separate because local fallback mode and offline CI do not require GROBID.

## 5. GitHub Gate

GitHub Actions runs `.github/workflows/ci.yml` on push and pull request. It also exposes `workflow_dispatch`, so the release gate can be triggered manually before a demo or release handoff.
