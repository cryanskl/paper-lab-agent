#!/usr/bin/env python3
"""Validate that requirements.txt declares project-owned direct dependencies."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REQUIREMENTS_PATH = REPO_ROOT / "requirements.txt"
REQUIRED_PACKAGES = [
    "fastapi",
    "uvicorn",
    "pydantic-settings",
    "python-multipart",
    "httpx",
    "requests",
    "apscheduler",
    "streamlit",
    "pytest",
    "pytest-asyncio",
]


def normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def declared_packages(path: Path = DEFAULT_REQUIREMENTS_PATH) -> set[str]:
    packages: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        package = re.split(r"\s*(?:==|>=|<=|~=|!=|>|<|\[)", line, maxsplit=1)[0].strip()
        if package:
            packages.add(normalize_package_name(package))
    return packages


def missing_required_packages(path: Path = DEFAULT_REQUIREMENTS_PATH) -> list[str]:
    declared = declared_packages(path)
    return [package for package in REQUIRED_PACKAGES if normalize_package_name(package) not in declared]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate required package declarations in requirements.txt.")
    parser.add_argument("requirements_path", nargs="?", default=str(DEFAULT_REQUIREMENTS_PATH))
    args = parser.parse_args()

    missing = missing_required_packages(Path(args.requirements_path))
    if missing:
        print(f"requirements missing packages: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
