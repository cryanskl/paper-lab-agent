#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


HEALTH_PATH = "/api/v1/health"
STATUS_PATH = "/api/v1/system/status"
EXTERNAL_STATUS_PATH = "/api/v1/system/status?check_external=true"
EXPECTED_API_PREFIX = "/api/v1"
EXPECTED_SERVICE = "paper-lab-agent"
STATUS_REQUIRED_KEYS = {
    "database_path",
    "runtime",
    "config_warnings",
    "storage",
    "storage_health",
    "external_capabilities",
    "counts",
}
CONFIG_WARNING_REQUIRED_KEYS = {"code", "capability", "message"}
RUNTIME_REQUIRED_KEYS = {"api_prefix", "scheduler_enabled", "scheduler_jobs", "version"}
SCHEDULER_JOB_REQUIRED_KEYS = {"id", "period", "trigger", "schedule", "timezone"}
STORAGE_REQUIRED_KEYS = {"data_dir", "pdf_dir", "tei_dir", "translation_dir", "export_dir", "vector_db_path"}
STORAGE_HEALTH_REQUIRED_KEYS = {
    "data_dir",
    "pdf_dir",
    "tei_dir",
    "translation_dir",
    "export_dir",
    "database",
    "database_parent",
    "vector_db_parent",
    "vector_db",
}
STORAGE_HEALTH_ENTRY_REQUIRED_KEYS = {"path", "exists", "writable"}
STORAGE_HEALTH_PATH_KEYS = {"data_dir", "pdf_dir", "tei_dir", "translation_dir", "export_dir"}
VECTOR_DB_HEALTH_REQUIRED_KEYS = {"path", "exists", "readable", "writable", "valid_json", "error"}
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


def default_frontend_url() -> str:
    if os.getenv("FRONTEND_URL"):
        return os.environ["FRONTEND_URL"].rstrip("/")
    host = os.getenv("STREAMLIT_HOST", "127.0.0.1")
    port = os.getenv("STREAMLIT_PORT", "8501")
    return f"http://{host}:{port}"


def streamlit_health_url(frontend_url: str) -> str:
    value = frontend_url.rstrip("/")
    if value.endswith("/_stcore/health"):
        return value
    return f"{value}/_stcore/health"


def fetch_json(url: str, timeout: float) -> dict:
    with urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_status(url: str, timeout: float) -> int:
    try:
        with urlopen(url, timeout=timeout) as response:
            return response.status
    except HTTPError as exc:
        return exc.code


def probe_frontend(frontend_url: str, timeout: float) -> dict:
    url = streamlit_health_url(frontend_url)
    try:
        return {"url": url, "status_code": fetch_status(url, timeout)}
    except (OSError, URLError) as exc:
        return {"url": url, "status_code": None, "error": str(exc)}


def validate_system_status(status: dict) -> list[str]:
    errors: list[str] = []
    missing = sorted(STATUS_REQUIRED_KEYS - set(status))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if "database_path" in status and (not isinstance(status["database_path"], str) or not status["database_path"]):
        errors.append("database_path must be a non-empty string")
    config_warnings = status.get("config_warnings")
    if not isinstance(config_warnings, list):
        errors.append("config_warnings must be a list")
    else:
        invalid_warnings = []
        for index, warning in enumerate(config_warnings):
            if not isinstance(warning, dict):
                invalid_warnings.append(str(index))
                continue
            missing_warning_keys = CONFIG_WARNING_REQUIRED_KEYS - set(warning)
            invalid_warnings.extend(f"{index}.{key}" for key in sorted(missing_warning_keys))
            invalid_warnings.extend(
                f"{index}.{key}"
                for key in sorted(CONFIG_WARNING_REQUIRED_KEYS & set(warning))
                if not isinstance(warning[key], str) or not warning[key].strip()
            )
        if invalid_warnings:
            errors.append(f"config_warnings invalid values: {', '.join(invalid_warnings)}")
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
        if "version" in runtime and (not isinstance(runtime["version"], str) or not runtime["version"]):
            invalid_runtime.append("version")
        if invalid_runtime:
            errors.append(f"runtime invalid values: {', '.join(sorted(invalid_runtime))}")
        if isinstance(runtime.get("api_prefix"), str) and runtime["api_prefix"] != EXPECTED_API_PREFIX:
            errors.append(f"runtime api_prefix must be {EXPECTED_API_PREFIX}")
        scheduler_jobs = runtime.get("scheduler_jobs")
        if not isinstance(scheduler_jobs, list):
            errors.append("scheduler_jobs must be a list")
        else:
            invalid_scheduler_jobs = []
            for index, job in enumerate(scheduler_jobs):
                if not isinstance(job, dict):
                    invalid_scheduler_jobs.append(str(index))
                    continue
                missing_job_keys = SCHEDULER_JOB_REQUIRED_KEYS - set(job)
                invalid_scheduler_jobs.extend(f"{index}.{key}" for key in sorted(missing_job_keys))
                invalid_scheduler_jobs.extend(
                    f"{index}.{key}"
                    for key in sorted(SCHEDULER_JOB_REQUIRED_KEYS & set(job))
                    if not isinstance(job[key], str) or not job[key].strip()
                )
            if invalid_scheduler_jobs:
                errors.append(f"scheduler_jobs invalid values: {', '.join(invalid_scheduler_jobs)}")
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
    storage_health = status.get("storage_health")
    if not isinstance(storage_health, dict):
        errors.append("storage_health must be an object")
    else:
        missing_storage_health = sorted(STORAGE_HEALTH_REQUIRED_KEYS - set(storage_health))
        if missing_storage_health:
            errors.append(f"storage_health missing keys: {', '.join(missing_storage_health)}")
        invalid_storage_health = []
        for key in sorted(STORAGE_HEALTH_REQUIRED_KEYS & set(storage_health)):
            value = storage_health[key]
            if not isinstance(value, dict):
                invalid_storage_health.append(key)
                continue
            missing_entry_keys = STORAGE_HEALTH_ENTRY_REQUIRED_KEYS - set(value)
            invalid_storage_health.extend(f"{key}.{entry_key}" for entry_key in sorted(missing_entry_keys))
            if "path" in value and (not isinstance(value["path"], str) or not value["path"]):
                invalid_storage_health.append(f"{key}.path")
            expected_path = storage.get(key) if isinstance(storage, dict) and key in STORAGE_HEALTH_PATH_KEYS else None
            if key == "database":
                expected_path = status.get("database_path")
            if (
                isinstance(expected_path, str)
                and expected_path
                and isinstance(value.get("path"), str)
                and value["path"] != expected_path
            ):
                source = "database_path" if key == "database" else f"storage.{key}"
                invalid_storage_health.append(f"{key}.path must match {source}")
            for entry_key in ("exists", "writable"):
                if entry_key in value and not isinstance(value[entry_key], bool):
                    invalid_storage_health.append(f"{key}.{entry_key}")
        if invalid_storage_health:
            errors.append(f"storage_health invalid values: {', '.join(invalid_storage_health)}")
        vector_db = storage_health.get("vector_db")
        if isinstance(vector_db, dict):
            invalid_vector_db = []
            missing_vector_db_keys = VECTOR_DB_HEALTH_REQUIRED_KEYS - set(vector_db)
            invalid_vector_db.extend(f"vector_db.{key}" for key in sorted(missing_vector_db_keys))
            if "path" in vector_db and (not isinstance(vector_db["path"], str) or not vector_db["path"]):
                invalid_vector_db.append("vector_db.path")
            expected_vector_db_path = storage.get("vector_db_path") if isinstance(storage, dict) else None
            if (
                isinstance(expected_vector_db_path, str)
                and expected_vector_db_path
                and isinstance(vector_db.get("path"), str)
                and vector_db["path"] != expected_vector_db_path
            ):
                invalid_vector_db.append("vector_db.path must match storage.vector_db_path")
            for entry_key in ("exists", "readable", "writable"):
                if entry_key in vector_db and not isinstance(vector_db[entry_key], bool):
                    invalid_vector_db.append(f"vector_db.{entry_key}")
            if "valid_json" in vector_db and vector_db["valid_json"] is not None and not isinstance(vector_db["valid_json"], bool):
                invalid_vector_db.append("vector_db.valid_json")
            if "error" in vector_db and vector_db["error"] is not None and not isinstance(vector_db["error"], str):
                invalid_vector_db.append("vector_db.error")
            if vector_db.get("exists") is True and vector_db.get("valid_json") is not True:
                invalid_vector_db.append("vector_db.valid_json")
                if vector_db.get("error"):
                    invalid_vector_db.append(str(vector_db["error"]))
            if invalid_vector_db:
                errors.append(f"storage_health invalid values: {', '.join(invalid_vector_db)}")
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
            invalid_grobid = []
            if "url" in grobid and (not isinstance(grobid["url"], str) or not grobid["url"]):
                invalid_grobid.append("url")
            if "available" in grobid and grobid["available"] is not None and not isinstance(grobid["available"], bool):
                invalid_grobid.append("available")
            if "status_code" in grobid and grobid["status_code"] is not None and (
                isinstance(grobid["status_code"], bool) or not isinstance(grobid["status_code"], int)
            ):
                invalid_grobid.append("status_code")
            if "error" in grobid and grobid["error"] is not None and not isinstance(grobid["error"], str):
                invalid_grobid.append("error")
            if invalid_grobid:
                errors.append(f"grobid invalid values: {', '.join(invalid_grobid)}")
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
    parser.add_argument("--check-frontend", action="store_true", help="Also check Streamlit frontend health")
    parser.add_argument("--frontend-url", default=default_frontend_url(), help="Streamlit base URL")
    parser.add_argument("--check-external", action="store_true", help="Also check configured external services")
    parser.add_argument("--require-grobid", action="store_true", help="Fail when GROBID is unavailable")
    parser.add_argument("--compact", action="store_true", help="Print health JSON on one line")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    status_path = EXTERNAL_STATUS_PATH if args.check_external or args.require_grobid else STATUS_PATH
    status_url = f"{base_url}{status_path}"
    try:
        health = fetch_json(f"{base_url}{HEALTH_PATH}", args.timeout)
        status = fetch_json(status_url, args.timeout)
    except (OSError, URLError, json.JSONDecodeError) as exc:
        print(f"health_check failed: {exc}", file=sys.stderr)
        return 1
    frontend = probe_frontend(args.frontend_url, args.timeout) if args.check_frontend else None

    config_warnings = status.get("config_warnings", []) if isinstance(status, dict) else []
    output = {"health": health, "status": status, "config_warnings": config_warnings}
    if frontend is not None:
        output["frontend"] = frontend
    print(json.dumps(output, ensure_ascii=False, indent=None if args.compact else 2))
    if not isinstance(health, dict):
        print("health_check failed: health response must be an object", file=sys.stderr)
        return 1
    if not isinstance(status, dict):
        print("health_check failed: system status response must be an object", file=sys.stderr)
        return 1
    if health.get("status") != "ok":
        print("health_check failed: API status is not ok", file=sys.stderr)
        return 1
    if health.get("service") != EXPECTED_SERVICE:
        print(f"health_check failed: health service must be {EXPECTED_SERVICE}", file=sys.stderr)
        return 1
    status_errors = validate_system_status(status)
    if status_errors:
        print(f"health_check failed: system status invalid ({'; '.join(status_errors)})", file=sys.stderr)
        return 1
    if args.require_grobid:
        grobid = status["external_capabilities"]["grobid"]
        if grobid.get("available") is not True:
            detail = grobid.get("error") or f"status_code={grobid.get('status_code')}"
            print(f"health_check failed: GROBID is required but unavailable ({detail})", file=sys.stderr)
            return 1
    if args.check_frontend and frontend["status_code"] != 200:
        detail = frontend.get("error") or f"status_code={frontend['status_code']}"
        print(
            f"health_check failed: Streamlit frontend is unavailable ({detail})",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
