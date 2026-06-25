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
PAGINATION_QUERY_PARAMS = ("page", "page_size")
PAGINATION_RESPONSE_FIELDS = ("items", "total", "page", "page_size")
PAGINATED_GET_PATHS = {
    "/api/v1/journals",
    "/api/v1/crawl/jobs",
    "/api/v1/papers",
    "/api/v1/categories",
    "/api/v1/documents",
    "/api/v1/documents/{}/sections",
    "/api/v1/documents/{}/chunks",
    "/api/v1/documents/{}/reaction-sets",
}
PAGINATED_DESCRIPTION_MARKERS = ("列出", "列表", "检索")
ASYNC_POST_PATHS = {
    "/api/v1/crawl/run",
    "/api/v1/documents/{}/parse",
    "/api/v1/documents/{}/translate",
    "/api/v1/documents/{}/index",
    "/api/v1/documents/{}/extract-chemistry",
}

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
    return [(method, display, normalized) for method, display, normalized, _description in documented_route_rows(path)]


def documented_route_rows(path: Path = DEFAULT_CONTRACT_PATH) -> list[tuple[str, str, str, str]]:
    routes: list[tuple[str, str, str, str]] = []
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
        description = cells[2] if len(cells) > 2 else ""
        routes.append((method, display_path(route_path), normalize_path(route_path), description))
    return routes


def app_openapi_paths() -> dict:
    from app.main import app

    return app.openapi()["paths"]


def app_openapi() -> dict:
    from app.main import app

    return app.openapi()


def app_routes() -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for path, methods in app_openapi_paths().items():
        if not str(path).startswith("/api/v1"):
            continue
        normalized_path = normalize_path(str(path))
        for method in methods.keys():
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


def is_paginated_documented_get(method: str, normalized: str, description: str) -> bool:
    if method != "GET":
        return False
    if normalized in PAGINATED_GET_PATHS:
        return True
    return any(marker in description for marker in PAGINATED_DESCRIPTION_MARKERS)


def normalized_openapi_specs(openapi_paths: dict | None = None) -> dict[tuple[str, str], dict]:
    paths = openapi_paths if openapi_paths is not None else app_openapi_paths()
    specs: dict[tuple[str, str], dict] = {}
    for path, methods in paths.items():
        normalized_path = normalize_path(str(path))
        for method, spec in methods.items():
            specs[(method.upper(), normalized_path)] = spec
    return specs


def resolve_openapi_ref(schema: dict, openapi: dict) -> dict:
    ref = schema.get("$ref") if isinstance(schema, dict) else None
    if not ref or not ref.startswith("#/"):
        return schema
    current: object = openapi
    for part in ref.removeprefix("#/").split("/"):
        if not isinstance(current, dict):
            return schema
        current = current.get(part)
    return current if isinstance(current, dict) else schema


def response_schema(spec: dict, openapi: dict | None = None) -> dict:
    schema = (
        spec.get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    return resolve_openapi_ref(schema, openapi or {})


def pagination_contract_issues(
    contract_path: Path = DEFAULT_CONTRACT_PATH,
    openapi_paths: dict | None = None,
) -> list[str]:
    specs = normalized_openapi_specs(openapi_paths)
    issues: list[str] = []
    for method, display, normalized, description in documented_route_rows(contract_path):
        if not is_paginated_documented_get(method, normalized, description):
            continue
        spec = specs.get((method, normalized))
        if spec is None:
            continue
        query_params = {
            parameter.get("name")
            for parameter in spec.get("parameters", [])
            if parameter.get("in") == "query"
        }
        missing = [name for name in PAGINATION_QUERY_PARAMS if name not in query_params]
        if missing:
            issues.append(f"{method} {display} missing query parameters: {', '.join(missing)}")
    return issues


def pagination_response_contract_issues(
    contract_path: Path = DEFAULT_CONTRACT_PATH,
    openapi_paths: dict | None = None,
    openapi: dict | None = None,
) -> list[str]:
    source_openapi = openapi if openapi is not None else (app_openapi() if openapi_paths is None else {})
    paths = openapi_paths if openapi_paths is not None else source_openapi.get("paths", {})
    specs = normalized_openapi_specs(paths)
    issues: list[str] = []
    for method, display, normalized, description in documented_route_rows(contract_path):
        if not is_paginated_documented_get(method, normalized, description):
            continue
        spec = specs.get((method, normalized))
        if spec is None:
            continue
        schema = response_schema(spec, source_openapi)
        properties = set(schema.get("properties", {}).keys())
        required = set(schema.get("required", []))
        present = properties | required
        missing = [name for name in PAGINATION_RESPONSE_FIELDS if name not in present]
        if missing:
            issues.append(f"{method} {display} missing response fields: {', '.join(missing)}")
    return issues


def async_response_contract_issues(
    contract_path: Path = DEFAULT_CONTRACT_PATH,
    openapi_paths: dict | None = None,
) -> list[str]:
    specs = normalized_openapi_specs(openapi_paths)
    issues: list[str] = []
    for method, display, normalized, _description in documented_route_rows(contract_path):
        if method != "POST" or normalized not in ASYNC_POST_PATHS:
            continue
        spec = specs.get((method, normalized))
        if spec is None:
            continue
        response_codes = {str(code) for code in spec.get("responses", {}).keys()}
        if "202" not in response_codes:
            issues.append(f"{method} {display} missing 202 response")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate documented API endpoints against FastAPI routes.")
    parser.add_argument("contract_path", nargs="?", default=str(DEFAULT_CONTRACT_PATH))
    args = parser.parse_args()

    missing = missing_documented_routes(Path(args.contract_path))
    undocumented = undocumented_app_routes(Path(args.contract_path))
    pagination_issues = pagination_contract_issues(Path(args.contract_path))
    pagination_response_issues = pagination_response_contract_issues(Path(args.contract_path))
    async_issues = async_response_contract_issues(Path(args.contract_path))
    if missing or undocumented or pagination_issues or pagination_response_issues or async_issues:
        if missing:
            print("api contract missing routes:", file=sys.stderr)
            for route in missing:
                print(f"- {route}", file=sys.stderr)
        if undocumented:
            print("api contract undocumented app routes:", file=sys.stderr)
            for route in undocumented:
                print(f"- {route}", file=sys.stderr)
        if pagination_issues:
            print("api contract pagination issues:", file=sys.stderr)
            for issue in pagination_issues:
                print(f"- {issue}", file=sys.stderr)
        if pagination_response_issues:
            print("api contract pagination response issues:", file=sys.stderr)
            for issue in pagination_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if async_issues:
            print("api contract async response issues:", file=sys.stderr)
            for issue in async_issues:
                print(f"- {issue}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
