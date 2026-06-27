#!/usr/bin/env python3
"""Validate that requirements.txt declares project-owned direct dependencies."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REQUIREMENTS_PATH = REPO_ROOT / "requirements.txt"
REQUIRED_PACKAGES = [
    "fastapi",
    "uvicorn",
    "pydantic",
    "pydantic-settings",
    "python-multipart",
    "httpx",
    "requests",
    "apscheduler",
    "streamlit",
    "pytest",
    "pytest-asyncio",
]
SOURCE_PATHS = [REPO_ROOT / "app", REPO_ROOT / "scripts", REPO_ROOT / "streamlit_app.py"]
LOCAL_MODULES = {"app", "scripts", "streamlit_app", "tests"}
FALLBACK_STDLIB_MODULES = {
    "__future__",
    "argparse",
    "ast",
    "asyncio",
    "collections",
    "contextlib",
    "datetime",
    "email",
    "fnmatch",
    "functools",
    "hashlib",
    "html",
    "importlib",
    "json",
    "logging",
    "math",
    "os",
    "pathlib",
    "re",
    "shlex",
    "sqlite3",
    "subprocess",
    "sys",
    "tempfile",
    "typing",
    "unicodedata",
    "urllib",
    "xml",
    "zipfile",
}
STDLIB_MODULES = set(FALLBACK_STDLIB_MODULES) | set(getattr(sys, "stdlib_module_names", set()))
IMPORT_PACKAGE_ALIASES = {
    "apscheduler": "apscheduler",
    "bs4": "beautifulsoup4",
    "fastapi": "fastapi",
    "httpx": "httpx",
    "pydantic": "pydantic",
    "pydantic_settings": "pydantic-settings",
    "pytest": "pytest",
    "requests": "requests",
    "streamlit": "streamlit",
}


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


def python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(file for file in path.rglob("*.py") if file.is_file()))
    return files


def imported_top_level_modules(paths: list[Path] = SOURCE_PATHS) -> set[str]:
    modules: set[str] = set()
    for path in python_files(paths):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name.split(".", 1)[0])
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module.split(".", 1)[0])
    return modules


def required_packages_from_imports(paths: list[Path] = SOURCE_PATHS) -> list[str]:
    packages: list[str] = []
    for module in sorted(imported_top_level_modules(paths)):
        if module in LOCAL_MODULES or module in STDLIB_MODULES:
            continue
        package = IMPORT_PACKAGE_ALIASES.get(module, module.replace("_", "-"))
        if package not in packages:
            packages.append(package)
    return packages


def missing_imported_packages(
    requirements_path: Path = DEFAULT_REQUIREMENTS_PATH,
    source_paths: list[Path] = SOURCE_PATHS,
) -> list[str]:
    declared = declared_packages(requirements_path)
    return [
        package
        for package in required_packages_from_imports(source_paths)
        if normalize_package_name(package) not in declared
    ]


def missing_required_packages(path: Path = DEFAULT_REQUIREMENTS_PATH) -> list[str]:
    declared = declared_packages(path)
    return [package for package in REQUIRED_PACKAGES if normalize_package_name(package) not in declared]


def first_symlink_parent(path: Path) -> Path | None:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        return parent
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate required package declarations in requirements.txt.")
    parser.add_argument("requirements_path", nargs="?", default=str(DEFAULT_REQUIREMENTS_PATH))
    args = parser.parse_args()

    requirements_path = Path(args.requirements_path)
    if not requirements_path.exists():
        print(f"requirements file not found: {requirements_path}", file=sys.stderr)
        return 1
    symlink_parent = first_symlink_parent(requirements_path)
    if symlink_parent is not None:
        print(f"requirements file parent is not a regular directory: {symlink_parent}", file=sys.stderr)
        return 1
    if requirements_path.is_symlink() or not requirements_path.is_file():
        print(f"requirements file is not a regular file: {requirements_path}", file=sys.stderr)
        return 1
    try:
        requirements_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"requirements file unreadable: {requirements_path}: {exc}", file=sys.stderr)
        return 1

    missing = missing_required_packages(requirements_path)
    missing_imports = missing_imported_packages(requirements_path)
    unpinned = unpinned_packages(requirements_path)
    duplicates = duplicate_packages(requirements_path)
    if missing or missing_imports or unpinned or duplicates:
        if missing:
            print(f"requirements missing packages: {', '.join(missing)}", file=sys.stderr)
        if missing_imports:
            print(f"requirements missing imported packages: {', '.join(missing_imports)}", file=sys.stderr)
        if unpinned:
            print(f"requirements unpinned packages: {', '.join(unpinned)}", file=sys.stderr)
        if duplicates:
            print(f"requirements duplicate packages: {', '.join(duplicates)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
