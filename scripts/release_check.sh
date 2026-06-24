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
"${PYTHON_CMD[@]}" -m py_compile scripts/health_check.py scripts/import_fixtures.py scripts/smoke_check.py scripts/validate_env_example.py streamlit_app.py
"${PYTHON_CMD[@]}" scripts/health_check.py --help >/dev/null
"${PYTHON_CMD[@]}" scripts/validate_env_example.py
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
SMOKE_JSON="$("${PYTHON_CMD[@]}" -m scripts.smoke_check)"
printf '%s\n' "${SMOKE_JSON}"
SMOKE_JSON="${SMOKE_JSON}" "${PYTHON_CMD[@]}" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["SMOKE_JSON"])
expected = {
    "crawl_job_status": "success",
    "translation_status": "done",
    "blocked_export_status": 409,
    "verified_export_format": "json",
    "runtime_version": "0.1.0",
    "config_warning_count": 3,
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
PY
"${PYTHON_CMD[@]}" -m pytest -q
