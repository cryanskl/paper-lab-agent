#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


HEALTH_PATH = "/api/v1/health"
STATUS_PATH = "/api/v1/system/status"
EXTERNAL_STATUS_PATH = "/api/v1/system/status?check_external=true"
EXPECTED_API_PREFIX = "/api/v1"
STATUS_REQUIRED_KEYS = {"database_path", "runtime", "storage", "external_capabilities", "counts"}
RUNTIME_REQUIRED_KEYS = {"api_prefix", "scheduler_enabled"}
STORAGE_REQUIRED_KEYS = {"data_dir", "pdf_dir", "tei_dir", "translation_dir", "export_dir", "vector_db_path"}
EXTERNAL_CAPABILITY_REQUIRED_KEYS = {
    "openalex_mailto",
    "unpaywall_email",
    "grobid_url",
    "grobid",
    "llm_api_key",
    "embedding_model",
}
GROBID_REQUIRED_KEYS = {"url", "available", "status_code", "error"}
COUNT_REQUIRED_KEYS = {
    "journals",
    "papers",
    "categories",
    "crawl_jobs",
    "documents",
    "sections",
    "translations",
    "chunks",
    "reaction_sets",
    "reactions",
}


def load_env_file(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def normalize_base_url(url: str) -> str:
    value = url.rstrip("/")
    if value.endswith(EXPECTED_API_PREFIX):
        return value[: -len(EXPECTED_API_PREFIX)]
    return value


def default_base_url() -> str:
    if os.getenv("API_BASE_URL"):
        return normalize_base_url(os.environ["API_BASE_URL"])
    host = os.getenv("API_HOST", "127.0.0.1")
    port = os.getenv("API_PORT", "8000")
    return f"http://{host}:{port}"


def fetch_json(url: str, timeout: float) -> dict:
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def validate_system_status(status: dict) -> list[str]:
    errors: list[str] = []
    missing = sorted(STATUS_REQUIRED_KEYS - set(status))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    runtime = status.get("runtime")
    if not isinstance(runtime, dict):
        errors.append("runtime must be an object")
    else:
        missing_runtime = sorted(RUNTIME_REQUIRED_KEYS - set(runtime))
        if missing_runtime:
            errors.append(f"runtime missing keys: {', '.join(missing_runtime)}")
        invalid_runtime = []
        if "api_prefix" in runtime and not isinstance(runtime["api_prefix"], str):
            invalid_runtime.append("api_prefix")
        if "scheduler_enabled" in runtime and not isinstance(runtime["scheduler_enabled"], bool):
            invalid_runtime.append("scheduler_enabled")
        if invalid_runtime:
            errors.append(f"runtime invalid values: {', '.join(sorted(invalid_runtime))}")
        if isinstance(runtime.get("api_prefix"), str) and runtime["api_prefix"] != EXPECTED_API_PREFIX:
            errors.append(f"runtime api_prefix must be {EXPECTED_API_PREFIX}")
    storage = status.get("storage")
    if not isinstance(storage, dict):
        errors.append("storage must be an object")
    else:
        missing_storage = sorted(STORAGE_REQUIRED_KEYS - set(storage))
        if missing_storage:
            errors.append(f"storage missing keys: {', '.join(missing_storage)}")
        invalid_storage = sorted(
            key for key in STORAGE_REQUIRED_KEYS & set(storage) if not isinstance(storage[key], str) or not storage[key]
        )
        if invalid_storage:
            errors.append(f"storage invalid values: {', '.join(invalid_storage)}")
    external_capabilities = status.get("external_capabilities")
    if not isinstance(external_capabilities, dict):
        errors.append("external_capabilities must be an object")
    else:
        missing_capabilities = sorted(EXTERNAL_CAPABILITY_REQUIRED_KEYS - set(external_capabilities))
        if missing_capabilities:
            errors.append(f"external_capabilities missing keys: {', '.join(missing_capabilities)}")
        invalid_capabilities = []
        for key in ("openalex_mailto", "unpaywall_email", "llm_api_key"):
            if key in external_capabilities and not isinstance(external_capabilities[key], bool):
                invalid_capabilities.append(key)
        for key in ("grobid_url", "embedding_model"):
            if key in external_capabilities and (
                not isinstance(external_capabilities[key], str) or not external_capabilities[key]
            ):
                invalid_capabilities.append(key)
        if invalid_capabilities:
            errors.append(f"external_capabilities invalid values: {', '.join(sorted(invalid_capabilities))}")
        grobid = external_capabilities.get("grobid")
        if not isinstance(grobid, dict):
            errors.append("grobid must be an object")
        else:
            missing_grobid = sorted(GROBID_REQUIRED_KEYS - set(grobid))
            if missing_grobid:
                errors.append(f"grobid missing keys: {', '.join(missing_grobid)}")
    counts = status.get("counts")
    if not isinstance(counts, dict):
        errors.append("counts must be an object")
    else:
        missing_counts = sorted(COUNT_REQUIRED_KEYS - set(counts))
        if missing_counts:
            errors.append(f"counts missing keys: {', '.join(missing_counts)}")
        invalid_counts = sorted(
            key for key, value in counts.items() if isinstance(value, bool) or not isinstance(value, int) or value < 0
        )
        if invalid_counts:
            errors.append(f"counts invalid values: {', '.join(invalid_counts)}")
    return errors


def main() -> int:
    load_env_file()
    parser = argparse.ArgumentParser(description="Check paper-lab-agent API health.")
    parser.add_argument("--base-url", default=default_base_url(), help="FastAPI base URL without /api/v1")
    parser.add_argument("--check-external", action="store_true", help="Also check configured external services")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    status_path = EXTERNAL_STATUS_PATH if args.check_external else STATUS_PATH
    status_url = f"{base_url}{status_path}"
    try:
        health = fetch_json(f"{base_url}{HEALTH_PATH}", args.timeout)
        status = fetch_json(status_url, args.timeout)
    except (OSError, URLError, json.JSONDecodeError) as exc:
        print(f"health_check failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"health": health, "status": status}, ensure_ascii=False, indent=2))
    if not isinstance(health, dict):
        print("health_check failed: health response must be an object", file=sys.stderr)
        return 1
    if not isinstance(status, dict):
        print("health_check failed: system status response must be an object", file=sys.stderr)
        return 1
    if health.get("status") != "ok":
        print("health_check failed: API status is not ok", file=sys.stderr)
        return 1
    status_errors = validate_system_status(status)
    if status_errors:
        print(f"health_check failed: system status invalid ({'; '.join(status_errors)})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
