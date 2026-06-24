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

bash -n scripts/dev.sh
"${PYTHON_CMD[@]}" -m py_compile scripts/health_check.py scripts/import_fixtures.py scripts/smoke_check.py streamlit_app.py
"${PYTHON_CMD[@]}" -m scripts.smoke_check
"${PYTHON_CMD[@]}" -m pytest -q
