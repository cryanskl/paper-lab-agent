#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
        for key in ("DATABASE_PATH", "GROBID_URL", "OPENALEX_MAILTO", "UNPAYWALL_EMAIL", "LLM_API_KEY"):
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


def run_checks(repo: Path = Path(".")) -> dict[str, Any]:
    repo = repo.resolve()
    checks = [
        check_python_version(),
        check_required_files(repo),
        check_env_example(repo),
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
