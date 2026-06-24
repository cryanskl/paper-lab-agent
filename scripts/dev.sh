#!/usr/bin/env bash
set -euo pipefail

if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
STREAMLIT_HOST="${STREAMLIT_HOST:-127.0.0.1}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"
API_BASE_URL="${API_BASE_URL:-http://${API_HOST}:${API_PORT}/api/v1}"
DEV_READY_TIMEOUT="${DEV_READY_TIMEOUT:-30}"
PYTHON="${PYTHON:-}"

if [[ -z "${PYTHON}" ]]; then
  if [[ -x ".venv/bin/python" ]]; then
    PYTHON=".venv/bin/python"
  else
    PYTHON="python"
  fi
fi

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then kill "${API_PID}" 2>/dev/null || true; fi
  if [[ -n "${STREAMLIT_PID:-}" ]]; then kill "${STREAMLIT_PID}" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

wait_for_service() {
  "${PYTHON}" - "$1" "$2" "$3" "$4" <<'PY'
import sys
import time
import os
from urllib.error import URLError
from urllib.request import urlopen

name = sys.argv[1]
url = sys.argv[2]
deadline = time.monotonic() + float(sys.argv[3])
pid = int(sys.argv[4])
if name == "API":
    exited_message = f"API process exited before becoming ready: {pid}"
    timeout_message = f"API failed to become ready: {url}"
elif name == "Streamlit":
    exited_message = f"Streamlit process exited before becoming ready: {pid}"
    timeout_message = f"Streamlit failed to become ready: {url}"
else:
    exited_message = f"{name} process exited before becoming ready: {pid}"
    timeout_message = f"{name} failed to become ready: {url}"
while time.monotonic() < deadline:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        print(exited_message, file=sys.stderr)
        raise SystemExit(1)
    try:
        with urlopen(url, timeout=1) as response:
            if response.status == 200:
                raise SystemExit(0)
    except (OSError, URLError):
        pass
    time.sleep(0.5)

print(timeout_message, file=sys.stderr)
raise SystemExit(1)
PY
}

wait_for_api() {
  wait_for_service "API" "$1" "$2" "$3"
}

"${PYTHON}" -m uvicorn app.main:app --host "${API_HOST}" --port "${API_PORT}" &
API_PID=$!

wait_for_api "http://${API_HOST}:${API_PORT}/api/v1/health" "${DEV_READY_TIMEOUT}" "${API_PID}"

API_BASE_URL="${API_BASE_URL}" "${PYTHON}" -m streamlit run streamlit_app.py \
  --server.address "${STREAMLIT_HOST}" \
  --server.port "${STREAMLIT_PORT}" \
  --server.headless true &
STREAMLIT_PID=$!

wait_for_service "Streamlit" "http://${STREAMLIT_HOST}:${STREAMLIT_PORT}/_stcore/health" "${DEV_READY_TIMEOUT}" "${STREAMLIT_PID}"

echo "FastAPI:   http://${API_HOST}:${API_PORT}"
echo "Streamlit: http://${STREAMLIT_HOST}:${STREAMLIT_PORT}"
echo "API_BASE_URL=${API_BASE_URL}"
echo "PYTHON=${PYTHON}"

wait
