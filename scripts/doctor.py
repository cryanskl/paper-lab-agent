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
)
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
        text = path.read_text(encoding="utf-8")
        for key in REQUIRED_ENV_EXAMPLE_KEYS:
            if f"{key}=" not in text:
                issues.append(
                    {
                        "code": "missing_env_example_key",
                        "key": key,
                        "message": f".env.example must document {key}",
                    }
                )
    return {
        "name": "env_example",
        "status": status_from_issues(issues),
        "issues": issues,
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


def check_writable_directory(key: str, path: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    try:
        if path.exists() and not path.is_dir():
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
