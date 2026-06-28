#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.release_readiness import RELEASE_BLOCKING_CONFIG_WARNING_CODES

HEALTH_PATH = "/api/v1/health"
STATUS_PATH = "/api/v1/system/status"
EXTERNAL_STATUS_PATH = "/api/v1/system/status?check_external=true"
OPENAPI_PATH = "/openapi.json"
EXPECTED_API_PREFIX = "/api/v1"
EXPECTED_SERVICE = "paper-lab-agent"
SUPPORTED_TRANSLATION_ADAPTERS = {"local-echo", "openai-compatible"}
OPENAPI_REQUIRED_TAGS = {"system"}
OPENAPI_REQUIRED_PATHS = {"/api/v1/health"}
OPENAPI_REQUIRED_SCHEMAS = {"ErrorResponse"}
STATUS_REQUIRED_KEYS = {
    "database_path",
    "runtime",
    "config_warnings",
    "storage",
    "storage_health",
    "external_capabilities",
    "demo_data",
    "release_readiness",
    "status_counts",
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
STORAGE_HEALTH_SUMMARY_KEYS = (
    "data_dir",
    "pdf_dir",
    "tei_dir",
    "translation_dir",
    "export_dir",
    "database",
    "database_parent",
    "vector_db_parent",
    "vector_db",
)
STORAGE_HEALTH_ENTRY_REQUIRED_KEYS = {"path", "exists", "writable"}
STORAGE_HEALTH_PATH_KEYS = {"data_dir", "pdf_dir", "tei_dir", "translation_dir", "export_dir"}
VECTOR_DB_HEALTH_REQUIRED_KEYS = {"path", "exists", "readable", "writable", "valid_json", "error"}
EXTERNAL_CAPABILITY_REQUIRED_KEYS = {
    "openalex_mailto",
    "unpaywall_email",
    "grobid_url",
    "grobid",
    "llm_api_key",
    "translation_adapter",
    "llm_model",
    "embedding_model",
    "vector_db_backend",
}
GROBID_REQUIRED_KEYS = {"url", "available", "status_code", "error"}
COUNT_REQUIRED_KEYS = {
    "journals",
    "papers",
    "categories",
    "paper_categories",
    "crawl_jobs",
    "documents",
    "sections",
    "translations",
    "chunks",
    "reaction_sets",
    "reactions",
    "reaction_audits",
}
STATUS_COUNT_REQUIRED_KEYS = {
    "crawl_jobs",
    "document_parse",
    "document_index",
    "document_chemistry",
    "translations",
    "reaction_sets",
}
DEMO_DATA_MIN_COUNTS = {
    "journals": 6,
    "papers": 1,
    "documents": 1,
    "sections": 1,
    "chunks": 1,
    "reaction_sets": 1,
    "reactions": 1,
}
DEMO_DATA_REQUIRED_KEYS = {"ready", "requirements", "missing", "counts"}
RELEASE_READINESS_REQUIRED_KEYS = {
    "ready",
    "demo_data_missing",
    "failed_workflows",
    "config_warning_codes",
    "storage_errors",
}
RELEASE_READINESS_LIST_KEYS = {
    "demo_data_missing",
    "failed_workflows",
    "config_warning_codes",
    "storage_errors",
}
ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def clean_env_value(value: str) -> str:
    result = []
    in_single = False
    in_double = False
    previous = ""
    for char in value:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double and (not result or previous.isspace()):
            break
        result.append(char)
        previous = char
    cleaned = "".join(result).strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
        return cleaned[1:-1]
    return cleaned


def load_env_file(path: Path = Path(".env")) -> Optional[str]:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        return f"env file is not a regular file: {path}"
    symlink_parent = first_symlink_parent(path)
    if symlink_parent is not None:
        return f"env file parent is not a regular directory: {symlink_parent}"
    if not path.exists():
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return f"failed to read env file {path}: {exc}"
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not ENV_KEY_PATTERN.fullmatch(key):
            continue
        value = clean_env_value(value)
        if key not in os.environ:
            os.environ[key] = value
    return None


def normalize_base_url(url: str) -> str:
    value = url.rstrip("/")
    if value.endswith(EXPECTED_API_PREFIX):
        return value[: -len(EXPECTED_API_PREFIX)]
    return value


def write_output_file(path: Path, rendered: str) -> Optional[str]:
    if path.is_symlink():
        return f"output path is not a regular file: {path}"
    symlink_parent = first_symlink_parent(path)
    if symlink_parent is not None:
        return f"output path parent is not a regular directory: {symlink_parent}"
    if path.exists() and not path.is_file():
        return f"output path is not a regular file: {path}"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{rendered}\n", encoding="utf-8")
    except OSError as exc:
        return f"failed to write output file {path}: {exc}"
    return None


def first_symlink_parent(path: Path) -> Optional[Path]:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        return parent
    return None


def connect_host(host: str) -> str:
    return "127.0.0.1" if host == "0.0.0.0" else host


def url_host(host: str) -> str:
    return f"[{host}]" if ":" in host and not host.startswith("[") else host


def default_base_url() -> str:
    if os.getenv("API_BASE_URL"):
        return normalize_base_url(os.environ["API_BASE_URL"])
    host = url_host(connect_host(os.getenv("API_HOST", "127.0.0.1")))
    port = os.getenv("API_PORT", "8000")
    return f"http://{host}:{port}"


def default_frontend_url() -> str:
    if os.getenv("FRONTEND_URL"):
        return os.environ["FRONTEND_URL"].rstrip("/")
    host = url_host(connect_host(os.getenv("STREAMLIT_HOST", "127.0.0.1")))
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


def validate_openapi_schema(openapi: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(openapi, dict):
        return ["openapi must be an object"]

    info = openapi.get("info")
    if not isinstance(info, dict):
        errors.append("info must be an object")
    elif info.get("title") != EXPECTED_SERVICE:
        errors.append(f"info.title must be {EXPECTED_SERVICE}")

    paths = openapi.get("paths")
    if not isinstance(paths, dict):
        errors.append("paths must be an object")
    else:
        missing_paths = sorted(OPENAPI_REQUIRED_PATHS - set(paths))
        if missing_paths:
            errors.append(f"missing paths: {', '.join(missing_paths)}")

    tags = openapi.get("tags")
    if not isinstance(tags, list):
        errors.append("tags must be a list")
    else:
        tag_names = {
            tag.get("name")
            for tag in tags
            if isinstance(tag, dict) and isinstance(tag.get("name"), str)
        }
        missing_tags = sorted(OPENAPI_REQUIRED_TAGS - tag_names)
        if missing_tags:
            errors.append(f"missing tags: {', '.join(missing_tags)}")

    components = openapi.get("components")
    schemas = components.get("schemas") if isinstance(components, dict) else None
    if not isinstance(schemas, dict):
        errors.append("components.schemas must be an object")
    else:
        missing_schemas = sorted(OPENAPI_REQUIRED_SCHEMAS - set(schemas))
        if missing_schemas:
            errors.append(f"missing schemas: {', '.join(missing_schemas)}")
    return errors


def probe_openapi(base_url: str, timeout: float) -> dict:
    url = f"{base_url}{OPENAPI_PATH}"
    try:
        payload = fetch_json(url, timeout)
    except (OSError, URLError, json.JSONDecodeError) as exc:
        return {"url": url, "ok": False, "error": str(exc), "path_count": 0, "tag_names": []}

    errors = validate_openapi_schema(payload)
    paths = payload.get("paths") if isinstance(payload, dict) else {}
    tags = payload.get("tags") if isinstance(payload, dict) else []
    tag_names = sorted(
        tag.get("name")
        for tag in tags
        if isinstance(tag, dict) and isinstance(tag.get("name"), str)
    )
    return {
        "url": url,
        "ok": errors == [],
        "error": "; ".join(errors) if errors else None,
        "path_count": len(paths) if isinstance(paths, dict) else 0,
        "tag_names": tag_names,
    }


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
            if (
                "actual" in warning
                and warning["actual"] is not None
                and (not isinstance(warning["actual"], str) or not warning["actual"].strip())
            ):
                invalid_warnings.append(f"{index}.actual")
            if "supported" in warning and warning["supported"] is not None:
                supported = warning["supported"]
                if not isinstance(supported, list):
                    invalid_warnings.append(f"{index}.supported")
                else:
                    invalid_warnings.extend(
                        f"{index}.supported.{item_index}"
                        for item_index, value in enumerate(supported)
                        if not isinstance(value, str) or not value.strip()
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
        for key in ("grobid_url", "embedding_model", "vector_db_backend"):
            if key in external_capabilities and (
                not isinstance(external_capabilities[key], str) or not external_capabilities[key]
            ):
                invalid_capabilities.append(key)
        if "translation_adapter" in external_capabilities and external_capabilities["translation_adapter"] not in SUPPORTED_TRANSLATION_ADAPTERS:
            invalid_capabilities.append("translation_adapter")
        if "llm_model" in external_capabilities and (
            not isinstance(external_capabilities["llm_model"], str) or not external_capabilities["llm_model"]
        ):
            invalid_capabilities.append("llm_model")
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
    demo_data = status.get("demo_data")
    if demo_data is not None and not isinstance(demo_data, dict):
        errors.append("demo_data must be an object")
    elif isinstance(demo_data, dict):
        missing_demo_keys = sorted(DEMO_DATA_REQUIRED_KEYS - set(demo_data))
        if missing_demo_keys:
            errors.append(f"demo_data missing keys: {', '.join(missing_demo_keys)}")
        invalid_demo_data = []
        if "ready" in demo_data and not isinstance(demo_data["ready"], bool):
            invalid_demo_data.append("ready")
        if "missing" in demo_data and not isinstance(demo_data["missing"], list):
            invalid_demo_data.append("missing")
        elif isinstance(demo_data.get("missing"), list):
            invalid_demo_data.extend(
                f"missing.{index}"
                for index, item in enumerate(demo_data["missing"])
                if not isinstance(item, str) or not item.strip()
            )
        for key in ("requirements", "counts"):
            value = demo_data.get(key)
            if not isinstance(value, dict):
                invalid_demo_data.append(key)
                continue
            invalid_demo_data.extend(
                f"{key}.{item_key}"
                for item_key, item_value in value.items()
                if (
                    not isinstance(item_key, str)
                    or not item_key.strip()
                    or isinstance(item_value, bool)
                    or not isinstance(item_value, int)
                    or item_value < 0
                )
            )
        if invalid_demo_data:
            errors.append(f"demo_data invalid values: {', '.join(invalid_demo_data)}")
    release_readiness = status.get("release_readiness")
    if release_readiness is not None and not isinstance(release_readiness, dict):
        errors.append("release_readiness must be an object")
    elif isinstance(release_readiness, dict):
        missing_release_readiness = sorted(RELEASE_READINESS_REQUIRED_KEYS - set(release_readiness))
        if missing_release_readiness:
            errors.append(f"release_readiness missing keys: {', '.join(missing_release_readiness)}")
        invalid_release_readiness = []
        if "ready" in release_readiness and not isinstance(release_readiness["ready"], bool):
            invalid_release_readiness.append("ready")
        for key in sorted(RELEASE_READINESS_LIST_KEYS & set(release_readiness)):
            value = release_readiness[key]
            if not isinstance(value, list):
                invalid_release_readiness.append(key)
                continue
            invalid_release_readiness.extend(
                f"{key}.{index}"
                for index, item in enumerate(value)
                if not isinstance(item, str) or not item.strip()
            )
        if invalid_release_readiness:
            errors.append(f"release_readiness invalid values: {', '.join(invalid_release_readiness)}")
    status_counts = status.get("status_counts")
    if not isinstance(status_counts, dict):
        errors.append("status_counts must be an object")
    else:
        missing_status_counts = sorted(STATUS_COUNT_REQUIRED_KEYS - set(status_counts))
        if missing_status_counts:
            errors.append(f"status_counts missing keys: {', '.join(missing_status_counts)}")
        invalid_status_counts = []
        for section, section_counts in status_counts.items():
            if not isinstance(section_counts, dict):
                invalid_status_counts.append(section)
                continue
            for state, value in section_counts.items():
                if not isinstance(state, str) or not state.strip() or isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    invalid_status_counts.append(f"{section}.{state}")
        if invalid_status_counts:
            errors.append(f"status_counts invalid values: {', '.join(invalid_status_counts)}")
    return errors


def storage_writability_errors(status: dict) -> list[str]:
    storage_health = status.get("storage_health")
    if not isinstance(storage_health, dict):
        return ["storage_health"]

    errors: list[str] = []
    required_writable = [
        "data_dir",
        "pdf_dir",
        "tei_dir",
        "translation_dir",
        "export_dir",
        "database_parent",
        "vector_db_parent",
    ]
    for key in required_writable:
        entry = storage_health.get(key)
        if not isinstance(entry, dict):
            errors.append(key)
            continue
        if entry.get("exists") is not True:
            errors.append(f"{key}.exists")
        if entry.get("writable") is not True:
            errors.append(f"{key}.writable")

    database = storage_health.get("database")
    if isinstance(database, dict) and database.get("exists") is True and database.get("writable") is not True:
        errors.append("database.writable")

    vector_db = storage_health.get("vector_db")
    if isinstance(vector_db, dict) and vector_db.get("exists") is True and vector_db.get("writable") is not True:
        errors.append("vector_db.writable")
    if isinstance(vector_db, dict) and vector_db.get("exists") is True and vector_db.get("valid_json") is not True:
        errors.append("vector_db.valid_json")

    return errors


def failed_workflow_errors(status: dict) -> list[str]:
    status_counts = status.get("status_counts")
    if not isinstance(status_counts, dict):
        return ["status_counts"]
    errors: list[str] = []
    for workflow, counts in status_counts.items():
        if not isinstance(counts, dict):
            continue
        for blocking_status in ("failed", "rejected"):
            count = counts.get(blocking_status)
            if isinstance(count, int) and not isinstance(count, bool) and count > 0:
                errors.append(f"{workflow}.{blocking_status}={count}")
    return errors


def config_warning_errors(status: dict) -> list[str]:
    config_warnings = status.get("config_warnings")
    if not isinstance(config_warnings, list):
        return ["config_warnings"]
    errors: list[str] = []
    for index, warning in enumerate(config_warnings):
        if isinstance(warning, dict) and isinstance(warning.get("code"), str) and warning["code"].strip():
            errors.append(warning["code"].strip())
        else:
            errors.append(str(index))
    return errors


def demo_data_errors(status: dict) -> list[str]:
    demo_data = status.get("demo_data")
    if isinstance(demo_data, dict):
        missing = demo_data.get("missing")
        if isinstance(missing, list):
            return [str(item) for item in missing if str(item).strip()]
        if demo_data.get("ready") is True:
            return []
    counts = status.get("counts")
    if not isinstance(counts, dict):
        return ["counts"]
    errors: list[str] = []
    for key, minimum in DEMO_DATA_MIN_COUNTS.items():
        value = counts.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            errors.append(f"{key}>={minimum}")
    return errors


def api_release_readiness(status: dict) -> Optional[dict]:
    readiness = status.get("release_readiness")
    if not isinstance(readiness, dict):
        return None
    return {
        "ready": readiness.get("ready") is True,
        "demo_data_missing": list_values(readiness.get("demo_data_missing")),
        "failed_workflows": list_values(readiness.get("failed_workflows")),
        "config_warning_codes": list_values(readiness.get("config_warning_codes")),
        "storage_errors": list_values(readiness.get("storage_errors")),
    }


def list_values(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def release_readiness_blockers(readiness: dict) -> list[str]:
    blockers: list[str] = []
    for key in ("demo_data_missing", "failed_workflows", "storage_errors"):
        blockers.extend(f"{key}:{value}" for value in readiness.get(key, []))
    blockers.extend(
        f"config_warning_codes:{value}"
        for value in readiness.get("config_warning_codes", [])
        if value in RELEASE_BLOCKING_CONFIG_WARNING_CODES
    )
    if blockers:
        return blockers
    if readiness.get("ready") is True:
        return []
    return ["ready=false"]


def storage_health_summary(status: dict) -> dict:
    storage_health = status.get("storage_health")
    if not isinstance(storage_health, dict):
        return {}

    summary: dict[str, dict] = {}
    for key in STORAGE_HEALTH_SUMMARY_KEYS:
        entry = storage_health.get(key)
        if not isinstance(entry, dict):
            continue
        compact_entry = {}
        path = entry.get("path")
        if isinstance(path, str):
            compact_entry["path"] = path
        for field in ("exists", "readable", "writable", "valid_json"):
            value = entry.get(field)
            if isinstance(value, bool):
                compact_entry[field] = value
        error = entry.get("error")
        if isinstance(error, str) and error.strip():
            compact_entry["error"] = error
        if compact_entry:
            summary[key] = compact_entry
    return summary


def config_warning_details(config_warnings: list) -> list[dict]:
    details = []
    for warning in config_warnings:
        if not isinstance(warning, dict):
            continue
        detail = {}
        for key in ("code", "capability", "message", "actual"):
            value = warning.get(key)
            if isinstance(value, str) and value.strip():
                detail[key] = value
        supported = warning.get("supported")
        if isinstance(supported, list):
            values = [value for value in supported if isinstance(value, str) and value.strip()]
            if values:
                detail["supported"] = values
        if {"code", "capability", "message"} <= set(detail):
            details.append(detail)
    return details


def probe_blocker(prefix: str, detail: Optional[dict]) -> Optional[str]:
    if not isinstance(detail, dict):
        return None
    if prefix == "frontend" and detail.get("status_code") == 200:
        return None
    if prefix == "grobid" and detail.get("available") is True:
        return None
    if prefix == "openapi" and detail.get("ok") is True:
        return None
    reason = detail.get("error")
    if not reason:
        reason = f"status_code={detail.get('status_code')}"
    return f"{prefix}:{reason}"


def health_summary(
    health: dict,
    status: dict,
    frontend: Optional[dict] = None,
    openapi: Optional[dict] = None,
) -> dict:
    safe_status = status if isinstance(status, dict) else {}
    runtime = safe_status.get("runtime")
    if not isinstance(runtime, dict):
        runtime = {}
    demo_data = safe_status.get("demo_data")
    if not isinstance(demo_data, dict):
        demo_data = {}
    config_warnings = safe_status.get("config_warnings")
    if not isinstance(config_warnings, list):
        config_warnings = []
    api_readiness = api_release_readiness(safe_status)
    if api_readiness is not None:
        storage_errors = api_readiness["storage_errors"]
        demo_data_missing = api_readiness["demo_data_missing"]
        failed_workflows = api_readiness["failed_workflows"]
        config_warning_codes = api_readiness["config_warning_codes"]
        release_ready = api_readiness["ready"]
    else:
        storage_errors = storage_writability_errors(safe_status)
        demo_data_missing = demo_data_errors(safe_status)
        failed_workflows = failed_workflow_errors(safe_status)
        config_warning_codes = [
            warning["code"].strip()
            for warning in config_warnings
            if isinstance(warning, dict) and isinstance(warning.get("code"), str) and warning["code"].strip()
        ]
        release_ready = not (storage_errors or failed_workflows or demo_data_missing)
    readiness_blockers = release_readiness_blockers(
        {
            "ready": release_ready,
            "demo_data_missing": demo_data_missing,
            "failed_workflows": failed_workflows,
            "config_warning_codes": config_warning_codes,
            "storage_errors": storage_errors,
        }
    )
    external_capabilities = safe_status.get("external_capabilities")
    grobid = external_capabilities.get("grobid") if isinstance(external_capabilities, dict) else None
    frontend_blocker = probe_blocker("frontend", frontend)
    openapi_blocker = probe_blocker("openapi", openapi)
    grobid_blocker = (
        probe_blocker("grobid", grobid)
        if isinstance(grobid, dict)
        and any(grobid.get(key) is not None for key in ("available", "status_code", "error"))
        else None
    )
    release_blockers = [*readiness_blockers]
    if frontend_blocker:
        release_blockers.append(frontend_blocker)
    if openapi_blocker:
        release_blockers.append(openapi_blocker)
    if grobid_blocker:
        release_blockers.append(grobid_blocker)
    summary = {
        "service": health.get("service") if isinstance(health, dict) else None,
        "api_status": health.get("status") if isinstance(health, dict) else None,
        "api_prefix": runtime.get("api_prefix"),
        "version": runtime.get("version"),
        "scheduler_enabled": runtime.get("scheduler_enabled"),
        "scheduler_job_count": len(runtime.get("scheduler_jobs") or []),
        "scheduler_job_ids": [
            job.get("id")
            for job in (runtime.get("scheduler_jobs") or [])
            if isinstance(job, dict) and isinstance(job.get("id"), str)
        ],
        "release_ready": release_blockers == [],
        "release_blockers": release_blockers,
        "demo_data_ready": demo_data.get("ready") is True,
        "demo_data_missing": demo_data_missing,
        "workflows_ok": failed_workflows == [],
        "failed_workflows": failed_workflows,
        "config_warning_count": len(config_warning_codes),
        "config_ready": config_warning_codes == [],
        "config_warning_codes": config_warning_codes,
        "config_warning_details": config_warning_details(config_warnings),
        "storage_writable": storage_errors == [],
        "storage_errors": storage_errors,
        "storage_health": storage_health_summary(safe_status),
    }
    if frontend is not None:
        summary.update(
            {
                "frontend_url": frontend.get("url"),
                "frontend_status_code": frontend.get("status_code"),
                "frontend_ok": frontend.get("status_code") == 200,
            }
        )
    if openapi is not None:
        summary.update(
            {
                "openapi_url": openapi.get("url"),
                "openapi_ok": openapi.get("ok") is True,
                "openapi_path_count": openapi.get("path_count"),
                "openapi_tag_names": openapi.get("tag_names") or [],
            }
        )
    if isinstance(grobid, dict) and any(
        grobid.get(key) is not None for key in ("available", "status_code", "error")
    ):
        summary.update(
            {
                "grobid_url": grobid.get("url"),
                "grobid_available": grobid.get("available"),
                "grobid_status_code": grobid.get("status_code"),
                "grobid_error": grobid.get("error"),
            }
        )
    return summary


def main() -> int:
    env_error = load_env_file()
    if env_error:
        print(f"health_check failed: {env_error}", file=sys.stderr)
        return 1
    parser = argparse.ArgumentParser(description="Check paper-lab-agent API health.")
    parser.add_argument("--base-url", default=default_base_url(), help="FastAPI base URL without /api/v1")
    parser.add_argument("--check-frontend", action="store_true", help="Also check Streamlit frontend health")
    parser.add_argument("--frontend-url", default=default_frontend_url(), help="Streamlit base URL")
    parser.add_argument("--require-frontend", action="store_true", help="Fail when Streamlit frontend is unavailable")
    parser.add_argument("--check-openapi", action="store_true", help="Also check live OpenAPI JSON schema")
    parser.add_argument("--require-openapi", action="store_true", help="Fail when OpenAPI JSON schema is unavailable or invalid")
    parser.add_argument("--check-external", action="store_true", help="Also check configured external services")
    parser.add_argument("--require-grobid", action="store_true", help="Fail when GROBID is unavailable")
    parser.add_argument("--require-storage-writable", action="store_true", help="Fail when local storage paths are missing or not writable")
    parser.add_argument(
        "--require-no-failed-workflows",
        action="store_true",
        help="Fail when workflow status counts include failed or rejected items",
    )
    parser.add_argument("--require-no-config-warnings", action="store_true", help="Fail when system status reports configuration warnings")
    parser.add_argument("--require-demo-data", action="store_true", help="Fail when walking skeleton demo data is not loaded")
    parser.add_argument(
        "--require-release-ready",
        action="store_true",
        help="Fail unless storage, workflows, configuration, and demo data are release-ready",
    )
    parser.add_argument("--compact", action="store_true", help="Print health JSON on one line")
    parser.add_argument("--summary-only", action="store_true", help="Print only release/demo readiness summary JSON")
    parser.add_argument("--output", type=Path, help="Also write the emitted health JSON to this file")
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
    frontend = probe_frontend(args.frontend_url, args.timeout) if args.check_frontend or args.require_frontend else None
    openapi = probe_openapi(base_url, args.timeout) if args.check_openapi or args.require_openapi else None

    config_warnings = status.get("config_warnings", []) if isinstance(status, dict) else []
    output = {"health": health, "status": status, "config_warnings": config_warnings}
    if frontend is not None:
        output["frontend"] = frontend
    if openapi is not None:
        output["openapi"] = openapi
    emitted = health_summary(health, status, frontend, openapi) if args.summary_only else output
    rendered = json.dumps(
        emitted,
        ensure_ascii=False,
        indent=None if args.compact else 2,
    )
    print(rendered)
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
    if args.output:
        output_error = write_output_file(args.output, rendered)
        if output_error:
            print(f"health_check failed: {output_error}", file=sys.stderr)
            return 1
    api_readiness = api_release_readiness(status)
    if args.require_release_ready and api_readiness is not None:
        readiness_errors = release_readiness_blockers(api_readiness)
        if readiness_errors:
            print(f"health_check failed: release readiness blockers present ({'; '.join(readiness_errors)})", file=sys.stderr)
            return 1
    if args.require_storage_writable or (args.require_release_ready and api_readiness is None):
        storage_errors = storage_writability_errors(status)
        if storage_errors:
            print(f"health_check failed: storage is not writable ({'; '.join(storage_errors)})", file=sys.stderr)
            return 1
    if args.require_no_failed_workflows or (args.require_release_ready and api_readiness is None):
        workflow_errors = failed_workflow_errors(status)
        if workflow_errors:
            print(f"health_check failed: failed workflows present ({'; '.join(workflow_errors)})", file=sys.stderr)
            return 1
    if args.require_no_config_warnings or (args.require_release_ready and api_readiness is None):
        warning_errors = config_warning_errors(status)
        if warning_errors:
            print(f"health_check failed: config warnings present ({'; '.join(warning_errors)})", file=sys.stderr)
            return 1
    if args.require_demo_data or (args.require_release_ready and api_readiness is None):
        demo_errors = demo_data_errors(status)
        if demo_errors:
            print(f"health_check failed: demo data is incomplete ({'; '.join(demo_errors)})", file=sys.stderr)
            return 1
    if args.require_frontend and isinstance(frontend, dict) and frontend.get("status_code") != 200:
        detail = frontend.get("error") or f"status_code={frontend.get('status_code')}"
        print(f"health_check failed: frontend is required but unavailable ({detail})", file=sys.stderr)
        return 1
    if args.require_openapi and isinstance(openapi, dict) and openapi.get("ok") is not True:
        detail = openapi.get("error") or "invalid OpenAPI schema"
        print(f"health_check failed: OpenAPI schema is unavailable or invalid ({detail})", file=sys.stderr)
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
    if args.check_openapi and isinstance(openapi, dict) and openapi.get("ok") is not True:
        detail = openapi.get("error") or "invalid OpenAPI schema"
        print(
            f"health_check failed: OpenAPI schema is unavailable or invalid ({detail})",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
