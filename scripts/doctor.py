#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


MIN_PYTHON = (3, 9)
REQUIRED_FILES = (
    "README.md",
    "requirements.txt",
    ".env.example",
    "docs/schema.sql",
    "docs/接口设计文档.md",
    "docs/PRD_等离子体文献系统.md",
    "scripts/dev.sh",
    "scripts/release_check.sh",
    "streamlit_app.py",
    "app/main.py",
)
PYTHON_DEPENDENCIES = (
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("pydantic", "pydantic"),
    ("pydantic-settings", "pydantic_settings"),
    ("python-multipart", "multipart"),
    ("httpx", "httpx"),
    ("requests", "requests"),
    ("apscheduler", "apscheduler"),
    ("streamlit", "streamlit"),
    ("pytest", "pytest"),
)
REQUIRED_ENV_EXAMPLE_KEYS = (
    "OPENALEX_MAILTO",
    "UNPAYWALL_EMAIL",
    "GROBID_URL",
    "LLM_API_KEY",
    "EMBEDDING_MODEL",
    "VECTOR_DB_PATH",
    "DATABASE_PATH",
    "PAPER_LAB_DATA_DIR",
    "PAPER_LAB_PDF_DIR",
    "PAPER_LAB_TEI_DIR",
    "PAPER_LAB_TRANSLATION_DIR",
    "PAPER_LAB_EXPORT_DIR",
    "VECTOR_DB_BACKEND",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "PAPER_LAB_SCHEDULER_ENABLED",
    "ACADEMIC_API_MAX_PAGES",
    "ACADEMIC_API_MAX_RETRIES",
    "ACADEMIC_API_RETRY_BACKOFF_SECONDS",
    "ACADEMIC_API_REQUEST_INTERVAL_SECONDS",
    "ACADEMIC_API_TIMEOUT_SECONDS",
    "UNPAYWALL_API_MAX_RETRIES",
    "UNPAYWALL_API_RETRY_BACKOFF_SECONDS",
    "UNPAYWALL_API_REQUEST_INTERVAL_SECONDS",
    "UNPAYWALL_API_TIMEOUT_SECONDS",
    "API_HOST",
    "API_PORT",
    "API_BASE_URL",
    "STREAMLIT_HOST",
    "STREAMLIT_PORT",
    "FRONTEND_URL",
    "DEV_READY_TIMEOUT",
)
SECRET_LIKE_ENV_EXAMPLE_KEYS = (
    "OPENALEX_MAILTO",
    "UNPAYWALL_EMAIL",
    "LLM_API_KEY",
)
ENV_EXAMPLE_DEFAULTS = {
    "PAPER_LAB_DATA_DIR": "data",
    "DATABASE_PATH": "data/plasma.db",
    "PAPER_LAB_PDF_DIR": "data/pdfs",
    "PAPER_LAB_TEI_DIR": "data/tei",
    "PAPER_LAB_TRANSLATION_DIR": "data/translations",
    "PAPER_LAB_EXPORT_DIR": "data/exports",
    "VECTOR_DB_PATH": "data/vector-index.json",
    "VECTOR_DB_BACKEND": "local-json",
    "GROBID_URL": "http://127.0.0.1:8070",
    "LLM_BASE_URL": "https://api.openai.com/v1",
    "LLM_MODEL": "gpt-4o-mini",
    "EMBEDDING_MODEL": "local-hash",
    "PAPER_LAB_SCHEDULER_ENABLED": "false",
    "ACADEMIC_API_MAX_PAGES": "3",
    "ACADEMIC_API_MAX_RETRIES": "3",
    "ACADEMIC_API_RETRY_BACKOFF_SECONDS": "0.25",
    "ACADEMIC_API_REQUEST_INTERVAL_SECONDS": "0.0",
    "ACADEMIC_API_TIMEOUT_SECONDS": "20.0",
    "UNPAYWALL_API_MAX_RETRIES": "3",
    "UNPAYWALL_API_RETRY_BACKOFF_SECONDS": "0.25",
    "UNPAYWALL_API_REQUEST_INTERVAL_SECONDS": "0.0",
    "UNPAYWALL_API_TIMEOUT_SECONDS": "20.0",
}
ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def status_from_issues(issues: list[dict[str, Any]]) -> str:
    return "fail" if issues else "pass"


def check_python_version() -> dict[str, Any]:
    version = sys.version_info
    issues: list[dict[str, Any]] = []
    if (version.major, version.minor) < MIN_PYTHON:
        issues.append(
            {
                "code": "unsupported_python_version",
                "message": f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required",
                "actual": f"{version.major}.{version.minor}.{version.micro}",
            }
        )
    return {
        "name": "python_version",
        "status": status_from_issues(issues),
        "value": f"{version.major}.{version.minor}.{version.micro}",
        "required": f">={MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
        "issues": issues,
    }


def check_required_files(repo: Path) -> dict[str, Any]:
    issues = []
    for rel_path in REQUIRED_FILES:
        path = repo / rel_path
        if not path.exists() or not path.is_file():
            issues.append(
                {
                    "code": "missing_required_file",
                    "path": rel_path,
                    "message": f"{rel_path} is required for local setup",
                }
            )
    return {
        "name": "required_files",
        "status": status_from_issues(issues),
        "required": list(REQUIRED_FILES),
        "issues": issues,
    }


def check_env_example(repo: Path) -> dict[str, Any]:
    path = repo / ".env.example"
    issues = []
    if path.exists() and path.is_file():
        values = env_example_values(path)
        keys = set(values)
        for key in REQUIRED_ENV_EXAMPLE_KEYS:
            if key not in keys:
                issues.append(
                    {
                        "code": "missing_env_example_key",
                        "key": key,
                        "message": f".env.example must document {key}",
                    }
                )
        for key in SECRET_LIKE_ENV_EXAMPLE_KEYS:
            if values.get(key):
                issues.append(
                    {
                        "code": "non_empty_env_example_secret",
                        "key": key,
                        "message": f".env.example must leave {key} blank",
                    }
                )
        for key, expected in ENV_EXAMPLE_DEFAULTS.items():
            actual = values.get(key)
            if actual is not None and not env_values_match(actual, expected):
                issues.append(
                    {
                        "code": "env_example_default_drift",
                        "key": key,
                        "expected": expected,
                        "actual": actual,
                        "message": f".env.example {key} must match default {expected}",
                    }
                )
        api_base_url_issue = api_base_url_runtime_issue(values)
        if api_base_url_issue is not None:
            issues.append(api_base_url_issue)
        frontend_url_issue = frontend_url_runtime_issue(values)
        if frontend_url_issue is not None:
            issues.append(frontend_url_issue)
        dev_ready_timeout_issue = dev_ready_timeout_runtime_issue(values, repo / "scripts/dev.sh")
        if dev_ready_timeout_issue is not None:
            issues.append(dev_ready_timeout_issue)
    return {
        "name": "env_example",
        "status": status_from_issues(issues),
        "issues": issues,
    }


def env_example_keys(path: Path) -> set[str]:
    return set(env_example_values(path))


def env_example_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        key, separator, _value = line.partition("=")
        key = key.strip()
        if separator and ENV_KEY_PATTERN.fullmatch(key):
            values[key] = _value.strip().strip('"').strip("'")
    return values


def normalize_env_value(value: str) -> str:
    if value.startswith("./"):
        return value[2:]
    return value


def env_values_match(actual: str, expected: str) -> bool:
    if normalize_env_value(actual) == normalize_env_value(expected):
        return True
    try:
        return float(actual) == float(expected)
    except ValueError:
        return False


def connect_host(host: str) -> str:
    return "127.0.0.1" if host == "0.0.0.0" else host


def url_host(host: str) -> str:
    return f"[{host}]" if ":" in host and not host.startswith("[") else host


def api_base_url_runtime_issue(values: dict[str, str]) -> dict[str, str] | None:
    api_host = values.get("API_HOST")
    api_port = values.get("API_PORT")
    api_base_url = values.get("API_BASE_URL")
    if not api_host or not api_port or not api_base_url:
        return None
    expected = f"http://{url_host(connect_host(api_host))}:{api_port}/api/v1"
    if api_base_url == expected:
        return None
    return {
        "code": "env_example_runtime_default_drift",
        "key": "API_BASE_URL",
        "expected": expected,
        "actual": api_base_url,
        "message": f".env.example API_BASE_URL must match runtime default {expected}",
    }


def frontend_url_runtime_issue(values: dict[str, str]) -> dict[str, str] | None:
    streamlit_host = values.get("STREAMLIT_HOST")
    streamlit_port = values.get("STREAMLIT_PORT")
    frontend_url = values.get("FRONTEND_URL")
    if not streamlit_host or not streamlit_port or not frontend_url:
        return None
    expected = f"http://{url_host(connect_host(streamlit_host))}:{streamlit_port}"
    if frontend_url == expected:
        return None
    return {
        "code": "env_example_runtime_default_drift",
        "key": "FRONTEND_URL",
        "expected": expected,
        "actual": frontend_url,
        "message": f".env.example FRONTEND_URL must match runtime default {expected}",
    }


def dev_ready_timeout_default(path: Path) -> str | None:
    if not path.exists():
        return None
    match = re.search(r'DEV_READY_TIMEOUT="\$\{DEV_READY_TIMEOUT:-([^}]+)\}"', path.read_text(encoding="utf-8"))
    if not match:
        return None
    return match.group(1)


def dev_ready_timeout_runtime_issue(values: dict[str, str], dev_script_path: Path) -> dict[str, str] | None:
    expected = dev_ready_timeout_default(dev_script_path)
    actual = values.get("DEV_READY_TIMEOUT")
    if not expected or not actual or actual == expected:
        return None
    return {
        "code": "env_example_runtime_default_drift",
        "key": "DEV_READY_TIMEOUT",
        "expected": expected,
        "actual": actual,
        "message": f".env.example DEV_READY_TIMEOUT must match runtime default {expected}",
    }


def check_python_dependencies() -> dict[str, Any]:
    issues = []
    for package, import_name in PYTHON_DEPENDENCIES:
        if importlib.util.find_spec(import_name) is None:
            issues.append(
                {
                    "code": "missing_python_dependency",
                    "package": package,
                    "import_name": import_name,
                    "message": f"Python dependency {package} is not importable as {import_name}",
                }
            )
    return {
        "name": "python_dependencies",
        "status": status_from_issues(issues),
        "required": [
            {"package": package, "import_name": import_name}
            for package, import_name in PYTHON_DEPENDENCIES
        ],
        "issues": issues,
    }


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


def env_with_file_values(repo: Path, env: dict[str, str] | None = None) -> dict[str, str]:
    merged = dict(os.environ if env is None else env)
    env_path = repo / ".env"
    if not env_path.exists() or not env_path.is_file():
        return merged
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not ENV_KEY_PATTERN.fullmatch(key) or key in merged:
            continue
        merged[key] = clean_env_value(value)
    return merged


def storage_path_config(repo: Path, env: dict[str, str] | None = None) -> dict[str, Path]:
    env = env_with_file_values(repo, env)
    data_dir = Path(env.get("PAPER_LAB_DATA_DIR") or "data")
    database_path = Path(env.get("DATABASE_PATH") or data_dir / "plasma.db")
    pdf_dir = Path(env.get("PAPER_LAB_PDF_DIR") or data_dir / "pdfs")
    tei_dir = Path(env.get("PAPER_LAB_TEI_DIR") or data_dir / "tei")
    translation_dir = Path(env.get("PAPER_LAB_TRANSLATION_DIR") or data_dir / "translations")
    export_dir = Path(env.get("PAPER_LAB_EXPORT_DIR") or data_dir / "exports")
    vector_db_path = Path(env.get("VECTOR_DB_PATH") or data_dir / "vector-index.json")
    paths = {
        "data_dir": data_dir,
        "database_parent": database_path.parent,
        "pdf_dir": pdf_dir,
        "tei_dir": tei_dir,
        "translation_dir": translation_dir,
        "export_dir": export_dir,
        "vector_db_parent": vector_db_path.parent,
    }
    return {
        key: path if path.is_absolute() else repo / path
        for key, path in paths.items()
    }


def first_symlink_parent(path: Path) -> Path | None:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        return parent
    return None


def check_writable_directory(key: str, path: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    try:
        if (
            path.is_symlink()
            or first_symlink_parent(path) is not None
            or (path.exists() and not path.is_dir())
        ):
            return [
                {
                    "code": "storage_path_not_directory",
                    "key": key,
                    "path": str(path),
                    "message": f"{key} must be a writable directory: {path}",
                }
            ]
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".paper-lab-doctor-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        issues.append(
            {
                "code": "storage_path_not_writable",
                "key": key,
                "path": str(path),
                "message": f"{key} must be writable: {exc}",
            }
        )
    return issues


def check_local_storage(repo: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    repo = repo.resolve()
    paths = storage_path_config(repo, env)
    issues = [
        issue
        for key, path in paths.items()
        for issue in check_writable_directory(key, path)
    ]
    return {
        "name": "local_storage",
        "status": status_from_issues(issues),
        "paths": {key: str(path) for key, path in paths.items()},
        "issues": issues,
    }


def run_checks(repo: Path = Path(".")) -> dict[str, Any]:
    repo = repo.resolve()
    checks = [
        check_python_version(),
        check_required_files(repo),
        check_env_example(repo),
        check_python_dependencies(),
        check_local_storage(repo),
    ]
    return {
        "ok": all(check["status"] == "pass" for check in checks),
        "repo": str(repo),
        "checks": checks,
    }


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    issues = [
        issue
        for check in payload["checks"]
        for issue in check.get("issues", [])
    ]
    return {
        "ok": payload["ok"],
        "repo": payload["repo"],
        "check_count": len(payload["checks"]),
        "issue_count": len(issues),
        "issue_codes": [issue.get("code") for issue in issues],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local setup preflight checks.")
    parser.add_argument("repo", nargs="?", default=".", type=Path)
    parser.add_argument("--compact", action="store_true", help="Print a compact summary JSON object.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when any preflight check fails.")
    args = parser.parse_args()

    payload = run_checks(args.repo)
    output = summary(payload) if args.compact else payload
    print(json.dumps(output, ensure_ascii=False, indent=None if args.compact else 2))
    return 1 if args.strict and not payload["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
