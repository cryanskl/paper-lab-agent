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

FIXTURE_DIR="$(mktemp -d -t paper-lab-fixtures-XXXXXX)"
cleanup() {
  rm -rf "${FIXTURE_DIR}"
}
trap cleanup EXIT

bash -n scripts/env.sh
bash -n scripts/dev.sh
"${PYTHON_CMD[@]}" -m py_compile scripts/health_check.py scripts/import_fixtures.py scripts/smoke_check.py streamlit_app.py
FIXTURE_JSON="$(PAPER_LAB_DATA_DIR="${FIXTURE_DIR}" "${PYTHON_CMD[@]}" scripts/import_fixtures.py)"
printf '%s\n' "${FIXTURE_JSON}"
FIXTURE_JSON="${FIXTURE_JSON}" "${PYTHON_CMD[@]}" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["FIXTURE_JSON"])
expected = {
    ("papers", "inserted"): 2,
    ("documents", "inserted"): 1,
}
for (section, key), value in expected.items():
    actual = payload.get(section, {}).get(key)
    if actual != value:
        print(f"release_check failed: fixture {section}.{key}={actual!r}, expected {value!r}", file=sys.stderr)
        raise SystemExit(1)
PY
SMOKE_JSON="$("${PYTHON_CMD[@]}" -m scripts.smoke_check)"
printf '%s\n' "${SMOKE_JSON}"
SMOKE_JSON="${SMOKE_JSON}" "${PYTHON_CMD[@]}" - <<'PY'
import json
import os
import sys

payload = json.loads(os.environ["SMOKE_JSON"])
expected = {
    "translation_status": "done",
    "blocked_export_status": 409,
    "verified_export_format": "json",
}
for key, value in expected.items():
    if payload.get(key) != value:
        print(f"release_check failed: smoke {key}={payload.get(key)!r}, expected {value!r}", file=sys.stderr)
        raise SystemExit(1)
if not payload.get("verified_export_path"):
    print("release_check failed: smoke verified_export_path is missing", file=sys.stderr)
    raise SystemExit(1)
PY
"${PYTHON_CMD[@]}" -m pytest -q
