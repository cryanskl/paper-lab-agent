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
ERROR_RESPONSE_FIELDS = ("error",)
ERROR_DETAIL_FIELDS = ("code", "message")
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
ASYNC_RESPONSE_FIELDS = ("job_id", "status")
ASYNC_JOBS_RESPONSE_PATHS = {"/api/v1/crawl/run"}
REQUIRED_SEMANTIC_ERROR_RESPONSES = {
    ("POST", "/api/v1/documents"): ("409", "415"),
    ("POST", "/api/v1/reaction-sets/{}/export"): ("400", "409"),
}
EXPORT_RESPONSE_FIELDS = (
    "reaction_set_id",
    "format",
    "output_path",
    "mime_type",
    "reaction_count",
    "audit_entry_count",
)
EXPORT_RESPONSE_ROUTE = ("POST", "/api/v1/reaction-sets/{}/export")
RAG_RESPONSE_FIELDS = ("answer", "sources")
RAG_SOURCE_FIELDS = (
    "document_id",
    "paper_id",
    "paper_title",
    "section_id",
    "section_seq",
    "section_title",
    "section_type",
    "chunk_id",
    "vector_id",
    "score",
    "source_excerpt",
)
RAG_RESPONSE_ROUTE = ("POST", "/api/v1/rag/query")
SYSTEM_STATUS_RESPONSE_ROUTE = ("GET", "/api/v1/system/status")
SYSTEM_STATUS_RESPONSE_FIELDS = (
    "database_path",
    "runtime",
    "config_warnings",
    "storage",
    "storage_health",
    "external_capabilities",
    "status_counts",
    "counts",
    "demo_data",
    "release_readiness",
)
SYSTEM_STATUS_NESTED_FIELDS = {
    "runtime": ("api_prefix", "scheduler_enabled", "scheduler_jobs", "version"),
    "demo_data": ("ready", "requirements", "missing", "counts"),
    "release_readiness": (
        "ready",
        "demo_data_missing",
        "failed_workflows",
        "config_warning_codes",
        "storage_errors",
    ),
    "external_capabilities": (
        "openalex_mailto",
        "unpaywall_email",
        "grobid_url",
        "grobid",
        "llm_api_key",
        "translation_adapter",
        "llm_model",
        "embedding_model",
        "vector_db_backend",
    ),
    "storage_health": (
        "data_dir",
        "pdf_dir",
        "tei_dir",
        "translation_dir",
        "export_dir",
        "database",
        "database_parent",
        "vector_db_parent",
        "vector_db",
    ),
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


def response_schema(spec: dict, openapi: dict | None = None, status_code: str = "200") -> dict:
    schema = (
        spec.get("responses", {})
        .get(status_code, {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    return resolve_openapi_ref(schema, openapi or {})


def schema_declares_fields(schema: dict, fields: tuple[str, ...]) -> bool:
    properties = set(schema.get("properties", {}).keys())
    required = set(schema.get("required", []))
    present = properties | required
    return all(field in present for field in fields)


def schema_property(schema: dict, field: str, openapi: dict) -> dict:
    return resolve_openapi_ref(schema.get("properties", {}).get(field, {}), openapi)


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


def error_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    issues: list[str] = []
    for path, methods in source_openapi.get("paths", {}).items():
        if not str(path).startswith("/api/v1"):
            continue
        for method, spec in methods.items():
            method_upper = method.upper()
            if method_upper not in HTTP_METHODS:
                continue
            for status_code, response in spec.get("responses", {}).items():
                if not str(status_code).isdigit() or int(status_code) < 400:
                    continue
                schema = response_schema({"responses": {str(status_code): response}}, source_openapi, str(status_code))
                error_schema = resolve_openapi_ref(schema.get("properties", {}).get("error", {}), source_openapi)
                if not schema_declares_fields(schema, ERROR_RESPONSE_FIELDS) or not schema_declares_fields(
                    error_schema,
                    ERROR_DETAIL_FIELDS,
                ):
                    issues.append(f"{method_upper} {path} {status_code} response must use unified error schema")
    return issues


def semantic_error_status_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    issues: list[str] = []
    for (method, normalized), required_statuses in REQUIRED_SEMANTIC_ERROR_RESPONSES.items():
        spec = specs.get((method, normalized))
        if spec is None:
            continue
        response_codes = {str(code) for code in spec.get("responses", {}).keys()}
        missing = [status for status in required_statuses if status not in response_codes]
        if missing:
            issues.append(f"{method} {normalized} missing error responses: {', '.join(missing)}")
    return issues


def export_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(EXPORT_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    missing = [field for field in EXPORT_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
    if not missing:
        return []
    method, path = EXPORT_RESPONSE_ROUTE
    return [f"{method} {path} missing response fields: {', '.join(missing)}"]


def rag_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(RAG_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    missing = [field for field in RAG_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
    method, path = RAG_RESPONSE_ROUTE
    if missing:
        return [f"{method} {path} missing response fields: {', '.join(missing)}"]

    sources_schema = resolve_openapi_ref(schema.get("properties", {}).get("sources", {}), source_openapi)
    source_item_schema = resolve_openapi_ref(sources_schema.get("items", {}), source_openapi)
    missing_source = [
        field for field in RAG_SOURCE_FIELDS if not schema_declares_fields(source_item_schema, (field,))
    ]
    if missing_source:
        return [f"{method} {path} missing source fields: {', '.join(missing_source)}"]
    return []


def system_status_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(SYSTEM_STATUS_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = SYSTEM_STATUS_RESPONSE_ROUTE
    missing = [
        field for field in SYSTEM_STATUS_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))
    ]
    if missing:
        return [f"{method} {path} missing response fields: {', '.join(missing)}"]

    for field, nested_fields in SYSTEM_STATUS_NESTED_FIELDS.items():
        nested_schema = schema_property(schema, field, source_openapi)
        missing_nested = [
            nested_field
            for nested_field in nested_fields
            if not schema_declares_fields(nested_schema, (nested_field,))
        ]
        if missing_nested:
            return [f"{method} {path} {field} missing fields: {', '.join(missing_nested)}"]
    return []


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


def async_response_body_contract_issues(
    contract_path: Path = DEFAULT_CONTRACT_PATH,
    openapi_paths: dict | None = None,
    openapi: dict | None = None,
) -> list[str]:
    source_openapi = openapi if openapi is not None else (app_openapi() if openapi_paths is None else {})
    paths = openapi_paths if openapi_paths is not None else source_openapi.get("paths", {})
    specs = normalized_openapi_specs(paths)
    issues: list[str] = []
    for method, display, normalized, _description in documented_route_rows(contract_path):
        if method != "POST" or normalized not in ASYNC_POST_PATHS:
            continue
        spec = specs.get((method, normalized))
        if spec is None:
            continue
        schema = response_schema(spec, source_openapi, "202")
        if normalized in ASYNC_JOBS_RESPONSE_PATHS:
            missing = [] if schema_declares_fields(schema, ("jobs",)) else ["jobs"]
            if missing:
                issues.append(f"{method} {display} missing 202 response fields: {', '.join(missing)}")
                continue
            jobs_schema = resolve_openapi_ref(schema.get("properties", {}).get("jobs", {}), source_openapi)
            item_schema = resolve_openapi_ref(jobs_schema.get("items", {}), source_openapi)
            missing_job_fields = [name for name in ASYNC_RESPONSE_FIELDS if not schema_declares_fields(item_schema, (name,))]
            if missing_job_fields:
                issues.append(f"{method} {display} missing 202 response job fields: {', '.join(missing_job_fields)}")
            continue
        missing = [name for name in ASYNC_RESPONSE_FIELDS if not schema_declares_fields(schema, (name,))]
        if missing:
            issues.append(f"{method} {display} missing 202 response fields: {', '.join(missing)}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate documented API endpoints against FastAPI routes.")
    parser.add_argument("contract_path", nargs="?", default=str(DEFAULT_CONTRACT_PATH))
    args = parser.parse_args()

    missing = missing_documented_routes(Path(args.contract_path))
    undocumented = undocumented_app_routes(Path(args.contract_path))
    pagination_issues = pagination_contract_issues(Path(args.contract_path))
    pagination_response_issues = pagination_response_contract_issues(Path(args.contract_path))
    error_response_issues = error_response_contract_issues()
    semantic_error_status_issues = semantic_error_status_contract_issues()
    export_response_issues = export_response_contract_issues()
    rag_response_issues = rag_response_contract_issues()
    system_status_response_issues = system_status_response_contract_issues()
    async_issues = async_response_contract_issues(Path(args.contract_path))
    async_body_issues = async_response_body_contract_issues(Path(args.contract_path))
    if (
        missing
        or undocumented
        or pagination_issues
        or pagination_response_issues
        or error_response_issues
        or semantic_error_status_issues
        or export_response_issues
        or rag_response_issues
        or system_status_response_issues
        or async_issues
        or async_body_issues
    ):
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
        if error_response_issues:
            print("api contract error response issues:", file=sys.stderr)
            for issue in error_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if semantic_error_status_issues:
            print("api contract semantic error status issues:", file=sys.stderr)
            for issue in semantic_error_status_issues:
                print(f"- {issue}", file=sys.stderr)
        if export_response_issues:
            print("api contract export response issues:", file=sys.stderr)
            for issue in export_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if rag_response_issues:
            print("api contract rag response issues:", file=sys.stderr)
            for issue in rag_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if system_status_response_issues:
            print("api contract system status response issues:", file=sys.stderr)
            for issue in system_status_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if async_issues:
            print("api contract async response issues:", file=sys.stderr)
            for issue in async_issues:
                print(f"- {issue}", file=sys.stderr)
        if async_body_issues:
            print("api contract async response body issues:", file=sys.stderr)
            for issue in async_body_issues:
                print(f"- {issue}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
