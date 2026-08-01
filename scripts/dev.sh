#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage: bash scripts/dev.sh

Starts the FastAPI service that hosts both the API and the native workbench,
waits for the health and workbench routes, then prints their URLs.

Environment variables:
  PYTHON                         Python executable, defaults to .venv/bin/python when present.
  API_HOST                       FastAPI bind host, default 127.0.0.1.
  API_PORT                       FastAPI port, default 8000.
  API_BASE_URL                   API health-check base URL override.
  DEV_READY_TIMEOUT              Seconds to wait for the service, default 30.
  DEV_EXIT_AFTER_READY           Set true to exit after the workbench is ready.
  PAPER_LAB_SCHEDULER_ENABLED    Set true to enable APScheduler crawl jobs.

After startup, verify the live gates with:
  python scripts/health_check.py --require-frontend
  python scripts/health_check.py --require-openapi

Workbench and API docs:
  http://127.0.0.1:8000/ui/
  http://127.0.0.1:8000/openapi.json
  http://127.0.0.1:8000/docs
  http://127.0.0.1:8000/redoc
EOF
  exit 0
fi

source "scripts/env.sh"

USER_API_BASE_URL="${API_BASE_URL:-}"
USER_API_HOST_SET="${API_HOST+x}"
USER_API_PORT_SET="${API_PORT+x}"

load_env_file_if_unset ".env"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
API_BASE_URL="$(resolve_api_base_url "${USER_API_BASE_URL}" "${USER_API_HOST_SET}" "${USER_API_PORT_SET}")"
API_CONNECT_HOST="$(resolve_connect_host "${API_HOST}")"
API_URL_HOST="$(format_url_host "${API_CONNECT_HOST}")"
DEV_READY_TIMEOUT="${DEV_READY_TIMEOUT:-30}"
DEV_EXIT_AFTER_READY="${DEV_EXIT_AFTER_READY:-false}"
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
}
trap cleanup EXIT INT TERM

wait_for_service() {
  "${PYTHON}" - "$1" "$2" "$3" "$4" <<'PY'
import os
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

name = sys.argv[1]
url = sys.argv[2]
deadline = time.monotonic() + float(sys.argv[3])
pid = int(sys.argv[4])
while time.monotonic() < deadline:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        print(f"{name} process exited before becoming ready: {pid}", file=sys.stderr)
        raise SystemExit(1)
    try:
        with urlopen(url, timeout=1) as response:
            if response.status == 200:
                raise SystemExit(0)
    except (OSError, URLError):
        pass
    time.sleep(0.5)

print(f"{name} failed to become ready: {url}", file=sys.stderr)
raise SystemExit(1)
PY
}

"${PYTHON}" -m uvicorn app.main:app --host "${API_HOST}" --port "${API_PORT}" &
API_PID=$!

wait_for_service "FastAPI" "http://${API_URL_HOST}:${API_PORT}/api/v1/health" "${DEV_READY_TIMEOUT}" "${API_PID}"
wait_for_service "Workbench" "http://${API_URL_HOST}:${API_PORT}/ui/" "${DEV_READY_TIMEOUT}" "${API_PID}"

echo "FastAPI:  http://${API_URL_HOST}:${API_PORT}"
echo "工作台:    http://${API_URL_HOST}:${API_PORT}/ui/"
echo "API_BASE_URL=${API_BASE_URL}"
echo "PYTHON=${PYTHON}"
echo "DEV_EXIT_AFTER_READY=${DEV_EXIT_AFTER_READY}"

if [[ "${DEV_EXIT_AFTER_READY}" == "true" ]]; then
  exit 0
fi

wait
