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


def requirement_lines(path: Path = DEFAULT_REQUIREMENTS_PATH) -> list[str]:
    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        lines.append(line)
    return lines


def package_name_from_requirement(line: str) -> str:
    return re.split(r"\s*(?:==|>=|<=|~=|!=|>|<|\[)", line, maxsplit=1)[0].strip()


def declared_packages(path: Path = DEFAULT_REQUIREMENTS_PATH) -> set[str]:
    packages: set[str] = set()
    for line in requirement_lines(path):
        package = package_name_from_requirement(line)
        if package:
            packages.add(normalize_package_name(package))
    return packages


def unpinned_packages(path: Path = DEFAULT_REQUIREMENTS_PATH) -> list[str]:
    packages: list[str] = []
    for line in requirement_lines(path):
        package = package_name_from_requirement(line)
        if package and "==" not in line:
            packages.append(normalize_package_name(package))
    return packages


def duplicate_packages(path: Path = DEFAULT_REQUIREMENTS_PATH) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for line in requirement_lines(path):
        package = re.split(r"\s*(?:==|>=|<=|~=|!=|>|<|\[)", line, maxsplit=1)[0].strip()
        normalized = normalize_package_name(package)
        if normalized in seen and normalized not in duplicates:
            duplicates.append(normalized)
        seen.add(normalized)
    return duplicates


def missing_required_packages(path: Path = DEFAULT_REQUIREMENTS_PATH) -> list[str]:
    declared = declared_packages(path)
    return [package for package in REQUIRED_PACKAGES if normalize_package_name(package) not in declared]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate required package declarations in requirements.txt.")
    parser.add_argument("requirements_path", nargs="?", default=str(DEFAULT_REQUIREMENTS_PATH))
    args = parser.parse_args()

    missing = missing_required_packages(Path(args.requirements_path))
    unpinned = unpinned_packages(Path(args.requirements_path))
    duplicates = duplicate_packages(Path(args.requirements_path))
    if missing or unpinned or duplicates:
        if missing:
            print(f"requirements missing packages: {', '.join(missing)}", file=sys.stderr)
        if unpinned:
            print(f"requirements unpinned packages: {', '.join(unpinned)}", file=sys.stderr)
        if duplicates:
            print(f"requirements duplicate packages: {', '.join(duplicates)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
