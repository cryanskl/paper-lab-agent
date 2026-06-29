#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

if [[ ! -f "scripts/env.sh" ]]; then
  echo "scripts/env.sh not found; run this script from the paper-lab-agent checkout." >&2
  exit 1
fi

source "scripts/env.sh"

if [[ ! -f ".env" && -f ".env.example" ]]; then
  cp ".env.example" ".env"
fi

load_env_file_if_unset ".env"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
STREAMLIT_HOST="${STREAMLIT_HOST:-127.0.0.1}"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"
DEV_READY_TIMEOUT="${DEV_READY_TIMEOUT:-45}"
DEV_EXIT_AFTER_READY="${DEV_EXIT_AFTER_READY:-false}"
START_OPEN_BROWSER="${START_OPEN_BROWSER:-true}"
PAPER_LAB_SCHEDULER_ENABLED="${PAPER_LAB_SCHEDULER_ENABLED:-false}"

API_CONNECT_HOST="$(resolve_connect_host "${API_HOST}")"
STREAMLIT_CONNECT_HOST="$(resolve_connect_host "${STREAMLIT_HOST}")"
API_URL_HOST="$(format_url_host "${API_CONNECT_HOST}")"
STREAMLIT_URL_HOST="$(format_url_host "${STREAMLIT_CONNECT_HOST}")"
API_BASE_URL="$(resolve_api_base_url "${API_BASE_URL:-}" "${API_HOST+x}" "${API_PORT+x}")"
BACKEND_HEALTH_URL="http://${API_URL_HOST}:${API_PORT}/api/v1/health"
FRONTEND_HEALTH_URL="http://${STREAMLIT_URL_HOST}:${STREAMLIT_PORT}/_stcore/health"
FRONTEND_URL="http://${STREAMLIT_URL_HOST}:${STREAMLIT_PORT}"

RUN_ID="$(date '+%Y%m%d-%H%M%S')"
LOG_DIR="${LOG_DIR:-logs/run-${RUN_ID}}"
mkdir -p "${LOG_DIR}"
STARTUP_LOG="${LOG_DIR}/startup.log"
BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
PID_FILE="${LOG_DIR}/pids.env"

exec > >(tee -a "${STARTUP_LOG}") 2>&1

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

choose_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    printf '%s\n' "${PYTHON}"
    return
  fi
  if [[ -x ".venv/bin/python" ]]; then
    printf '%s\n' ".venv/bin/python"
    return
  fi
  if command_exists python3; then
    printf '%s\n' "python3"
    return
  fi
  printf '%s\n' "python"
}

USER_PYTHON="${PYTHON:-}"
PYTHON="$(choose_python)"

if [[ -z "${PYTHON:-}" ]]; then
  echo "No Python executable found. Install Python 3.11+ or set PYTHON=/path/to/python." >&2
  exit 1
fi

if [[ ! -d ".venv" && -z "${USER_PYTHON}" && "${PYTHON}" != ".venv/bin/python" ]]; then
  echo "Creating Python virtual environment: .venv"
  "${PYTHON}" -m venv ".venv"
  PYTHON=".venv/bin/python"
fi

reset_port() {
  local label="$1"
  local port="$2"
  local pids
  local remaining

  pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -z "${pids}" ]]; then
    echo "${label} port ${port} is free."
    return
  fi

  echo "${label} port ${port} is occupied by PID(s): ${pids//$'\n'/ }. Resetting..."
  kill ${pids} 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    sleep 1
    remaining="$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
    if [[ -z "${remaining}" ]]; then
      echo "${label} port ${port} has been released."
      return
    fi
  done

  remaining="$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "${remaining}" ]]; then
    echo "${label} port ${port} still occupied by PID(s): ${remaining//$'\n'/ }. Forcing reset..."
    kill -9 ${remaining} 2>/dev/null || true
  fi
}

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then
    kill "${API_PID}" 2>/dev/null || true
  fi
  if [[ -n "${STREAMLIT_PID:-}" ]]; then
    kill "${STREAMLIT_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

wait_for_service() {
  "${PYTHON}" - "$1" "$2" "$3" "$4" "$5" <<'PY'
import os
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

name = sys.argv[1]
url = sys.argv[2]
deadline = time.monotonic() + float(sys.argv[3])
pid = int(sys.argv[4])
log_path = Path(sys.argv[5])

while time.monotonic() < deadline:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        print(f"{name} process exited before becoming ready: {pid}", file=sys.stderr)
        if log_path.exists():
            print(f"{name} log: {log_path}", file=sys.stderr)
            print(log_path.read_text(encoding="utf-8", errors="replace")[-2000:], file=sys.stderr)
        raise SystemExit(1)
    try:
        with urlopen(url, timeout=1) as response:
            if response.status == 200:
                raise SystemExit(0)
    except (OSError, URLError):
        pass
    time.sleep(0.5)

print(f"{name} failed to become ready: {url}", file=sys.stderr)
if log_path.exists():
    print(f"{name} log: {log_path}", file=sys.stderr)
    print(log_path.read_text(encoding="utf-8", errors="replace")[-2000:], file=sys.stderr)
raise SystemExit(1)
PY
}

open_url() {
  local url="$1"
  if [[ "${START_OPEN_BROWSER}" != "true" ]]; then
    echo "Browser auto-open disabled: START_OPEN_BROWSER=${START_OPEN_BROWSER}"
    return
  fi
  if command_exists open; then
    open "${url}"
  elif command_exists xdg-open; then
    xdg-open "${url}" >/dev/null 2>&1 &
  else
    echo "No browser opener found. Open manually: ${url}"
  fi
}

echo "paper-lab-agent startup"
echo "Project: ${ROOT_DIR}"
echo "Logs: ${LOG_DIR}"
echo "Python: ${PYTHON}"

echo "Installing backend/frontend Python dependencies from requirements.txt..."
"${PYTHON}" -m pip install -r requirements.txt

reset_port "FastAPI" "${API_PORT}"
reset_port "Streamlit" "${STREAMLIT_PORT}"

echo "Starting FastAPI backend..."
PAPER_LAB_SCHEDULER_ENABLED="${PAPER_LAB_SCHEDULER_ENABLED}" \
  "${PYTHON}" -m uvicorn app.main:app --host "${API_HOST}" --port "${API_PORT}" \
  >"${BACKEND_LOG}" 2>&1 &
API_PID=$!

wait_for_service "FastAPI" "${BACKEND_HEALTH_URL}" "${DEV_READY_TIMEOUT}" "${API_PID}" "${BACKEND_LOG}"

echo "Starting Streamlit frontend..."
API_BASE_URL="${API_BASE_URL}" \
  "${PYTHON}" -m streamlit run streamlit_app.py \
  --server.address "${STREAMLIT_HOST}" \
  --server.port "${STREAMLIT_PORT}" \
  --server.headless true \
  >"${FRONTEND_LOG}" 2>&1 &
STREAMLIT_PID=$!

wait_for_service "Streamlit" "${FRONTEND_HEALTH_URL}" "${DEV_READY_TIMEOUT}" "${STREAMLIT_PID}" "${FRONTEND_LOG}"

{
  echo "API_PID=${API_PID}"
  echo "STREAMLIT_PID=${STREAMLIT_PID}"
  echo "API_URL=http://${API_URL_HOST}:${API_PORT}"
  echo "STREAMLIT_URL=${FRONTEND_URL}"
  echo "API_BASE_URL=${API_BASE_URL}"
} > "${PID_FILE}"

echo "FastAPI:   http://${API_URL_HOST}:${API_PORT}"
echo "Streamlit: ${FRONTEND_URL}"
echo "API_BASE_URL=${API_BASE_URL}"
echo "Backend log: ${BACKEND_LOG}"
echo "Frontend log: ${FRONTEND_LOG}"
echo "Startup log: ${STARTUP_LOG}"

open_url "${FRONTEND_URL}"

if [[ "${DEV_EXIT_AFTER_READY}" == "true" ]]; then
  echo "DEV_EXIT_AFTER_READY=true; services verified, exiting and cleaning child processes."
  exit 0
fi

echo "Services are running. Press Ctrl+C in this terminal to stop them."
wait
