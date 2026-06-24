#!/usr/bin/env python3
"""Validate that API endpoints documented in docs/接口设计文档.md exist in FastAPI."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTRACT_PATH = REPO_ROOT / "docs" / "接口设计文档.md"
HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def normalize_path(path: str) -> str:
    value = path.strip().strip("`").split("?", 1)[0].rstrip("/")
    if not value.startswith("/"):
        value = f"/{value}"
    if not value.startswith("/api/v1/") and value != "/api/v1":
        value = f"/api/v1{value}"
    return re.sub(r"\{[^}/]+\}", "{}", value)


def display_path(path: str) -> str:
    value = path.strip().strip("`").split("?", 1)[0].rstrip("/")
    if not value.startswith("/"):
        value = f"/{value}"
    if not value.startswith("/api/v1/") and value != "/api/v1":
        value = f"/api/v1{value}"
    return value


def documented_routes(path: Path = DEFAULT_CONTRACT_PATH) -> list[tuple[str, str, str]]:
    routes: list[tuple[str, str, str]] = []
    endpoint_pattern = re.compile(r"`([^`]+)`")
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        method = cells[0].upper()
        if method not in HTTP_METHODS:
            continue
        match = endpoint_pattern.search(cells[1])
        if not match:
            continue
        route_path = match.group(1)
        routes.append((method, display_path(route_path), normalize_path(route_path)))
    return routes


def app_routes() -> set[tuple[str, str]]:
    from app.main import app

    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods or not str(path).startswith("/api/v1"):
            continue
        normalized_path = normalize_path(str(path))
        for method in methods:
            method = method.upper()
            if method in HTTP_METHODS:
                routes.add((method, normalized_path))
    return routes


def missing_documented_routes(contract_path: Path = DEFAULT_CONTRACT_PATH) -> list[str]:
    actual = app_routes()
    missing: list[str] = []
    for method, display, normalized in documented_routes(contract_path):
        if (method, normalized) not in actual:
            missing.append(f"{method} {display}")
    return missing


def undocumented_app_routes(contract_path: Path = DEFAULT_CONTRACT_PATH) -> list[str]:
    documented = {(method, normalized) for method, _display, normalized in documented_routes(contract_path)}
    undocumented: list[str] = []
    for method, normalized in sorted(app_routes()):
        if (method, normalized) not in documented:
            undocumented.append(f"{method} {normalized}")
    return undocumented


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate documented API endpoints against FastAPI routes.")
    parser.add_argument("contract_path", nargs="?", default=str(DEFAULT_CONTRACT_PATH))
    args = parser.parse_args()

    missing = missing_documented_routes(Path(args.contract_path))
    undocumented = undocumented_app_routes(Path(args.contract_path))
    if missing or undocumented:
        if missing:
            print("api contract missing routes:", file=sys.stderr)
            for route in missing:
                print(f"- {route}", file=sys.stderr)
        if undocumented:
            print("api contract undocumented app routes:", file=sys.stderr)
            for route in undocumented:
                print(f"- {route}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
