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
HEALTH_RESPONSE_ROUTE = ("GET", "/api/v1/health")
HEALTH_RESPONSE_FIELDS = ("status", "service")
JOURNAL_LIST_RESPONSE_ROUTE = ("GET", "/api/v1/journals")
JOURNAL_CRUD_RESPONSE_ROUTES = (
    ("POST", "/api/v1/journals", "201"),
    ("GET", "/api/v1/journals/{}", "200"),
    ("PUT", "/api/v1/journals/{}", "200"),
    ("DELETE", "/api/v1/journals/{}", "200"),
)
JOURNAL_RESPONSE_FIELDS = (
    "id",
    "name",
    "publisher",
    "platform",
    "url",
    "issn_print",
    "issn_electronic",
    "keywords",
    "year_from",
    "year_to",
    "sci_zone",
    "impact_factor",
    "active",
    "created_at",
    "updated_at",
)
CATEGORY_LIST_RESPONSE_ROUTE = ("GET", "/api/v1/categories")
CATEGORY_CREATE_RESPONSE_ROUTE = ("POST", "/api/v1/categories", "201")
CATEGORY_RESPONSE_FIELDS = ("id", "name", "slug", "description", "parent_id", "children")
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
REACTION_SET_DETAIL_RESPONSE_ROUTE = ("GET", "/api/v1/reaction-sets/{}")
REACTION_SET_LIST_RESPONSE_ROUTE = ("GET", "/api/v1/documents/{}/reaction-sets")
REACTION_SET_DETAIL_RESPONSE_FIELDS = (
    "id",
    "document_id",
    "name",
    "gas_mixture",
    "lxcat_db",
    "source_note",
    "status",
    "created_at",
    "reactions",
    "reaction_count",
    "verified_count",
    "unverified_count",
    "export_ready",
)
REACTION_SET_LIST_ITEM_FIELDS = (
    "id",
    "document_id",
    "name",
    "gas_mixture",
    "lxcat_db",
    "source_note",
    "status",
    "verified_by",
    "verified_at",
    "created_at",
    "reaction_count",
    "verified_count",
    "unverified_count",
    "export_ready",
)
REACTION_DETAIL_FIELDS = (
    "id",
    "reaction_set_id",
    "reaction",
    "reactants",
    "products",
    "reaction_type",
    "rate_type",
    "rate_value",
    "threshold_ev",
    "cross_section_url",
    "source_section_id",
    "source_section_title",
    "source_section_type",
    "source_section_seq",
    "source_label",
    "source_excerpt",
    "confidence",
    "verified",
    "audit_log",
)
DOCUMENT_RESPONSE_ROUTES = (
    ("GET", "/api/v1/documents/{}", "200"),
    ("POST", "/api/v1/documents", "201"),
)
DOCUMENT_LIST_RESPONSE_ROUTE = ("GET", "/api/v1/documents")
DOCUMENT_RESPONSE_FIELDS = (
    "id",
    "paper_id",
    "file_path",
    "file_hash",
    "original_name",
    "num_pages",
    "parse_status",
    "parse_error",
    "index_status",
    "index_error",
    "chemistry_status",
    "chemistry_error",
    "tei_path",
    "created_at",
    "paper",
)
DOCUMENT_PAPER_FIELDS = ("id", "doi", "title", "journal_name", "published_date")
SECTION_LIST_RESPONSE_ROUTE = ("GET", "/api/v1/documents/{}/sections")
SECTION_RESPONSE_FIELDS = ("id", "document_id", "parent_id", "seq", "title", "content", "section_type")
CHUNK_LIST_RESPONSE_ROUTE = ("GET", "/api/v1/documents/{}/chunks")
CHUNK_LIST_RESPONSE_FIELDS = ("items", "total", "page", "page_size", "indexed", "index_status", "index_error")
CHUNK_RESPONSE_FIELDS = (
    "id",
    "document_id",
    "section_id",
    "seq",
    "text",
    "token_count",
    "vector_id",
    "embedded",
    "created_at",
    "section_title",
)
TRANSLATION_RESPONSE_ROUTE = ("GET", "/api/v1/documents/{}/translation")
TRANSLATION_RESPONSE_FIELDS = (
    "id",
    "document_id",
    "source_lang",
    "target_lang",
    "status",
    "output_path",
    "error",
    "created_at",
)
PAPER_DETAIL_RESPONSE_ROUTE = ("GET", "/api/v1/papers/{}")
PAPER_LIST_RESPONSE_ROUTE = ("GET", "/api/v1/papers")
PAPER_MUTATION_RESPONSE_ROUTES = (
    ("POST", "/api/v1/papers/{}/resolve-oa"),
    ("POST", "/api/v1/papers/{}/classify"),
    ("PUT", "/api/v1/papers/{}/categories"),
)
PAPER_DETAIL_RESPONSE_FIELDS = (
    "id",
    "doi",
    "title",
    "abstract",
    "authors",
    "journal_id",
    "journal_name",
    "published_date",
    "published_year",
    "oa_status",
    "oa_pdf_url",
    "landing_url",
    "source_api",
    "dedupe_key",
    "has_doi",
    "dedupe_strategy",
    "categories",
    "category_details",
    "raw_metadata",
)
PAPER_LIST_ITEM_RESPONSE_FIELDS = tuple(
    field for field in PAPER_DETAIL_RESPONSE_FIELDS if field != "raw_metadata"
)
PAPER_CATEGORY_DETAIL_FIELDS = ("id", "slug", "name", "confidence", "method")
CRAWL_JOB_DETAIL_RESPONSE_ROUTE = ("GET", "/api/v1/crawl/jobs/{}")
CRAWL_JOB_LIST_RESPONSE_ROUTE = ("GET", "/api/v1/crawl/jobs")
CRAWL_JOB_DETAIL_RESPONSE_FIELDS = (
    "id",
    "journal_id",
    "period",
    "date_from",
    "date_to",
    "status",
    "papers_found",
    "papers_filtered",
    "papers_new",
    "error",
    "started_at",
    "finished_at",
    "created_at",
    "journal",
    "diagnostics",
)
CRAWL_JOB_JOURNAL_FIELDS = ("id", "name", "issn_print", "issn_electronic", "active")
CRAWL_JOB_DIAGNOSTIC_FIELDS = (
    "journal_id",
    "journal_name",
    "period",
    "date_from",
    "date_to",
    "status",
    "papers_found",
    "papers_filtered",
    "papers_new",
    "papers_accepted",
    "papers_existing",
    "outcome",
    "keyword_mode",
    "keyword_terms",
    "error",
)

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
    return effective_schema(resolve_openapi_ref(schema.get("properties", {}).get(field, {}), openapi), openapi)


def effective_schema(schema: dict, openapi: dict) -> dict:
    resolved = resolve_openapi_ref(schema, openapi)
    if not isinstance(resolved, dict):
        return {}
    for key in ("anyOf", "oneOf"):
        variants = resolved.get(key)
        if isinstance(variants, list):
            for variant in variants:
                candidate = effective_schema(variant, openapi)
                if candidate.get("type") != "null":
                    return candidate
    return resolved


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


def health_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(HEALTH_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = HEALTH_RESPONSE_ROUTE
    missing = [field for field in HEALTH_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
    if missing:
        return [f"{method} {path} missing response fields: {', '.join(missing)}"]
    return []


def journal_list_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(JOURNAL_LIST_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = JOURNAL_LIST_RESPONSE_ROUTE
    missing_page = [field for field in PAGINATION_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
    if missing_page:
        return [f"{method} {path} missing response fields: {', '.join(missing_page)}"]

    items_schema = schema_property(schema, "items", source_openapi)
    item_schema = effective_schema(items_schema.get("items", {}), source_openapi)
    missing_item = [field for field in JOURNAL_RESPONSE_FIELDS if not schema_declares_fields(item_schema, (field,))]
    if missing_item:
        return [f"{method} {path} item fields missing: {', '.join(missing_item)}"]
    return []


def journal_crud_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    issues: list[str] = []
    for method, path, status_code in JOURNAL_CRUD_RESPONSE_ROUTES:
        spec = specs.get((method, path))
        if spec is None:
            continue
        schema = response_schema(spec, source_openapi, status_code)
        missing = [field for field in JOURNAL_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
        if missing:
            issues.append(f"{method} {path} missing response fields: {', '.join(missing)}")
    return issues


def category_list_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(CATEGORY_LIST_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = CATEGORY_LIST_RESPONSE_ROUTE
    missing_page = [field for field in PAGINATION_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
    if missing_page:
        return [f"{method} {path} missing response fields: {', '.join(missing_page)}"]

    items_schema = schema_property(schema, "items", source_openapi)
    item_schema = effective_schema(items_schema.get("items", {}), source_openapi)
    missing_item = [field for field in CATEGORY_RESPONSE_FIELDS if not schema_declares_fields(item_schema, (field,))]
    if missing_item:
        return [f"{method} {path} item fields missing: {', '.join(missing_item)}"]

    children_schema = schema_property(item_schema, "children", source_openapi)
    child_schema = effective_schema(children_schema.get("items", {}), source_openapi)
    missing_child = [field for field in CATEGORY_RESPONSE_FIELDS if not schema_declares_fields(child_schema, (field,))]
    if missing_child:
        return [f"{method} {path} item child fields missing: {', '.join(missing_child)}"]
    return []


def category_create_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    method, path, status_code = CATEGORY_CREATE_RESPONSE_ROUTE
    spec = specs.get((method, path))
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi, status_code)
    missing = [field for field in CATEGORY_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
    if missing:
        return [f"{method} {path} missing response fields: {', '.join(missing)}"]
    return []


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


def reaction_set_detail_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(REACTION_SET_DETAIL_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = REACTION_SET_DETAIL_RESPONSE_ROUTE
    missing = [
        field for field in REACTION_SET_DETAIL_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))
    ]
    if missing:
        return [f"{method} {path} missing response fields: {', '.join(missing)}"]

    reactions_schema = schema_property(schema, "reactions", source_openapi)
    reaction_item_schema = resolve_openapi_ref(reactions_schema.get("items", {}), source_openapi)
    missing_reaction = [
        field for field in REACTION_DETAIL_FIELDS if not schema_declares_fields(reaction_item_schema, (field,))
    ]
    if missing_reaction:
        return [f"{method} {path} reaction fields missing: {', '.join(missing_reaction)}"]

    return []


def reaction_set_list_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(REACTION_SET_LIST_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = REACTION_SET_LIST_RESPONSE_ROUTE
    missing_page = [field for field in PAGINATION_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
    if missing_page:
        return [f"{method} {path} missing response fields: {', '.join(missing_page)}"]

    items_schema = schema_property(schema, "items", source_openapi)
    item_schema = effective_schema(items_schema.get("items", {}), source_openapi)
    missing_item = [
        field for field in REACTION_SET_LIST_ITEM_FIELDS if not schema_declares_fields(item_schema, (field,))
    ]
    if missing_item:
        return [f"{method} {path} item fields missing: {', '.join(missing_item)}"]
    return []


def document_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    for method, path, status_code in DOCUMENT_RESPONSE_ROUTES:
        spec = specs.get((method, path))
        if spec is None:
            continue
        schema = response_schema(spec, source_openapi, status_code)
        missing = [field for field in DOCUMENT_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
        if missing:
            return [f"{method} {path} missing response fields: {', '.join(missing)}"]

        paper_schema = schema_property(schema, "paper", source_openapi)
        missing_paper = [
            field for field in DOCUMENT_PAPER_FIELDS if not schema_declares_fields(paper_schema, (field,))
        ]
        if missing_paper:
            return [f"{method} {path} paper fields missing: {', '.join(missing_paper)}"]
    return []


def document_list_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(DOCUMENT_LIST_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = DOCUMENT_LIST_RESPONSE_ROUTE
    missing_page = [field for field in PAGINATION_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
    if missing_page:
        return [f"{method} {path} missing response fields: {', '.join(missing_page)}"]

    items_schema = schema_property(schema, "items", source_openapi)
    item_schema = effective_schema(items_schema.get("items", {}), source_openapi)
    missing_item = [field for field in DOCUMENT_RESPONSE_FIELDS if not schema_declares_fields(item_schema, (field,))]
    if missing_item:
        return [f"{method} {path} item fields missing: {', '.join(missing_item)}"]

    paper_schema = schema_property(item_schema, "paper", source_openapi)
    missing_paper = [
        field for field in DOCUMENT_PAPER_FIELDS if not schema_declares_fields(paper_schema, (field,))
    ]
    if missing_paper:
        return [f"{method} {path} item paper fields missing: {', '.join(missing_paper)}"]
    return []


def section_list_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(SECTION_LIST_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = SECTION_LIST_RESPONSE_ROUTE
    missing_page = [field for field in PAGINATION_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
    if missing_page:
        return [f"{method} {path} missing response fields: {', '.join(missing_page)}"]

    items_schema = schema_property(schema, "items", source_openapi)
    item_schema = effective_schema(items_schema.get("items", {}), source_openapi)
    missing_item = [field for field in SECTION_RESPONSE_FIELDS if not schema_declares_fields(item_schema, (field,))]
    if missing_item:
        return [f"{method} {path} item fields missing: {', '.join(missing_item)}"]
    return []


def chunk_list_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(CHUNK_LIST_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = CHUNK_LIST_RESPONSE_ROUTE
    missing_response = [
        field for field in CHUNK_LIST_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))
    ]
    if missing_response:
        return [f"{method} {path} missing response fields: {', '.join(missing_response)}"]

    items_schema = schema_property(schema, "items", source_openapi)
    item_schema = effective_schema(items_schema.get("items", {}), source_openapi)
    missing_item = [field for field in CHUNK_RESPONSE_FIELDS if not schema_declares_fields(item_schema, (field,))]
    if missing_item:
        return [f"{method} {path} item fields missing: {', '.join(missing_item)}"]
    return []


def translation_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(TRANSLATION_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = TRANSLATION_RESPONSE_ROUTE
    missing = [
        field for field in TRANSLATION_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))
    ]
    if missing:
        return [f"{method} {path} missing response fields: {', '.join(missing)}"]
    return []


def paper_detail_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(PAPER_DETAIL_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = PAPER_DETAIL_RESPONSE_ROUTE
    missing = [
        field for field in PAPER_DETAIL_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))
    ]
    if missing:
        return [f"{method} {path} missing response fields: {', '.join(missing)}"]

    categories_schema = schema_property(schema, "category_details", source_openapi)
    category_schema = effective_schema(categories_schema.get("items", {}), source_openapi)
    missing_category = [
        field for field in PAPER_CATEGORY_DETAIL_FIELDS if not schema_declares_fields(category_schema, (field,))
    ]
    if missing_category:
        return [f"{method} {path} category detail fields missing: {', '.join(missing_category)}"]
    return []


def paper_mutation_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    issues: list[str] = []
    for method, path in PAPER_MUTATION_RESPONSE_ROUTES:
        spec = specs.get((method, path))
        if spec is None:
            continue
        schema = response_schema(spec, source_openapi)
        missing = [
            field for field in PAPER_DETAIL_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))
        ]
        if missing:
            issues.append(f"{method} {path} missing response fields: {', '.join(missing)}")
            continue

        categories_schema = schema_property(schema, "category_details", source_openapi)
        category_schema = effective_schema(categories_schema.get("items", {}), source_openapi)
        missing_category = [
            field for field in PAPER_CATEGORY_DETAIL_FIELDS if not schema_declares_fields(category_schema, (field,))
        ]
        if missing_category:
            issues.append(f"{method} {path} category detail fields missing: {', '.join(missing_category)}")
    return issues


def paper_list_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(PAPER_LIST_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = PAPER_LIST_RESPONSE_ROUTE
    missing_page = [field for field in PAGINATION_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
    if missing_page:
        return [f"{method} {path} missing response fields: {', '.join(missing_page)}"]

    items_schema = schema_property(schema, "items", source_openapi)
    item_schema = effective_schema(items_schema.get("items", {}), source_openapi)
    missing_item = [
        field for field in PAPER_LIST_ITEM_RESPONSE_FIELDS if not schema_declares_fields(item_schema, (field,))
    ]
    if missing_item:
        return [f"{method} {path} item fields missing: {', '.join(missing_item)}"]

    categories_schema = schema_property(item_schema, "category_details", source_openapi)
    category_schema = effective_schema(categories_schema.get("items", {}), source_openapi)
    missing_category = [
        field for field in PAPER_CATEGORY_DETAIL_FIELDS if not schema_declares_fields(category_schema, (field,))
    ]
    if missing_category:
        return [f"{method} {path} item category detail fields missing: {', '.join(missing_category)}"]
    return []


def crawl_job_detail_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(CRAWL_JOB_DETAIL_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = CRAWL_JOB_DETAIL_RESPONSE_ROUTE
    missing = [
        field for field in CRAWL_JOB_DETAIL_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))
    ]
    if missing:
        return [f"{method} {path} missing response fields: {', '.join(missing)}"]

    journal_schema = schema_property(schema, "journal", source_openapi)
    missing_journal = [
        field for field in CRAWL_JOB_JOURNAL_FIELDS if not schema_declares_fields(journal_schema, (field,))
    ]
    if missing_journal:
        return [f"{method} {path} journal fields missing: {', '.join(missing_journal)}"]

    diagnostics_schema = schema_property(schema, "diagnostics", source_openapi)
    missing_diagnostics = [
        field for field in CRAWL_JOB_DIAGNOSTIC_FIELDS if not schema_declares_fields(diagnostics_schema, (field,))
    ]
    if missing_diagnostics:
        return [f"{method} {path} diagnostics fields missing: {', '.join(missing_diagnostics)}"]
    return []


def crawl_job_list_response_contract_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    specs = normalized_openapi_specs(source_openapi.get("paths", {}))
    spec = specs.get(CRAWL_JOB_LIST_RESPONSE_ROUTE)
    if spec is None:
        return []
    schema = response_schema(spec, source_openapi)
    method, path = CRAWL_JOB_LIST_RESPONSE_ROUTE
    missing_page = [field for field in PAGINATION_RESPONSE_FIELDS if not schema_declares_fields(schema, (field,))]
    if missing_page:
        return [f"{method} {path} missing response fields: {', '.join(missing_page)}"]

    items_schema = schema_property(schema, "items", source_openapi)
    item_schema = effective_schema(items_schema.get("items", {}), source_openapi)
    missing_item = [
        field for field in CRAWL_JOB_DETAIL_RESPONSE_FIELDS if not schema_declares_fields(item_schema, (field,))
    ]
    if missing_item:
        return [f"{method} {path} item fields missing: {', '.join(missing_item)}"]

    diagnostics_schema = schema_property(item_schema, "diagnostics", source_openapi)
    missing_diagnostics = [
        field for field in CRAWL_JOB_DIAGNOSTIC_FIELDS if not schema_declares_fields(diagnostics_schema, (field,))
    ]
    if missing_diagnostics:
        return [f"{method} {path} item diagnostics fields missing: {', '.join(missing_diagnostics)}"]
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


def empty_success_response_schema_issues(openapi: dict | None = None) -> list[str]:
    source_openapi = openapi if openapi is not None else app_openapi()
    issues: list[str] = []
    for path, methods in source_openapi.get("paths", {}).items():
        if not str(path).startswith("/api/v1"):
            continue
        normalized_path = normalize_path(str(path))
        for method, spec in methods.items():
            method_upper = method.upper()
            if method_upper not in HTTP_METHODS:
                continue
            for status_code, response in spec.get("responses", {}).items():
                if not str(status_code).isdigit() or not (200 <= int(status_code) < 300):
                    continue
                schema = (
                    response.get("content", {})
                    .get("application/json", {})
                    .get("schema")
                )
                if not schema or not resolve_openapi_ref(schema, source_openapi):
                    issues.append(
                        f"{method_upper} {normalized_path} {status_code} response must declare a non-empty schema"
                    )
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
    health_response_issues = health_response_contract_issues()
    journal_list_response_issues = journal_list_response_contract_issues()
    journal_crud_response_issues = journal_crud_response_contract_issues()
    category_list_response_issues = category_list_response_contract_issues()
    category_create_response_issues = category_create_response_contract_issues()
    export_response_issues = export_response_contract_issues()
    rag_response_issues = rag_response_contract_issues()
    system_status_response_issues = system_status_response_contract_issues()
    reaction_set_detail_response_issues = reaction_set_detail_response_contract_issues()
    reaction_set_list_response_issues = reaction_set_list_response_contract_issues()
    document_response_issues = document_response_contract_issues()
    document_list_response_issues = document_list_response_contract_issues()
    section_list_response_issues = section_list_response_contract_issues()
    chunk_list_response_issues = chunk_list_response_contract_issues()
    translation_response_issues = translation_response_contract_issues()
    paper_detail_response_issues = paper_detail_response_contract_issues()
    paper_mutation_response_issues = paper_mutation_response_contract_issues()
    paper_list_response_issues = paper_list_response_contract_issues()
    crawl_job_detail_response_issues = crawl_job_detail_response_contract_issues()
    crawl_job_list_response_issues = crawl_job_list_response_contract_issues()
    async_issues = async_response_contract_issues(Path(args.contract_path))
    async_body_issues = async_response_body_contract_issues(Path(args.contract_path))
    empty_success_schema_issues = empty_success_response_schema_issues()
    if (
        missing
        or undocumented
        or pagination_issues
        or pagination_response_issues
        or error_response_issues
        or semantic_error_status_issues
        or health_response_issues
        or journal_list_response_issues
        or journal_crud_response_issues
        or category_list_response_issues
        or category_create_response_issues
        or export_response_issues
        or rag_response_issues
        or system_status_response_issues
        or reaction_set_detail_response_issues
        or reaction_set_list_response_issues
        or document_response_issues
        or document_list_response_issues
        or section_list_response_issues
        or chunk_list_response_issues
        or translation_response_issues
        or paper_detail_response_issues
        or paper_mutation_response_issues
        or paper_list_response_issues
        or crawl_job_detail_response_issues
        or crawl_job_list_response_issues
        or async_issues
        or async_body_issues
        or empty_success_schema_issues
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
        if health_response_issues:
            print("api contract health response issues:", file=sys.stderr)
            for issue in health_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if journal_list_response_issues:
            print("api contract journal list response issues:", file=sys.stderr)
            for issue in journal_list_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if journal_crud_response_issues:
            print("api contract journal crud response issues:", file=sys.stderr)
            for issue in journal_crud_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if category_list_response_issues:
            print("api contract category list response issues:", file=sys.stderr)
            for issue in category_list_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if category_create_response_issues:
            print("api contract category create response issues:", file=sys.stderr)
            for issue in category_create_response_issues:
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
        if reaction_set_detail_response_issues:
            print("api contract reaction set detail response issues:", file=sys.stderr)
            for issue in reaction_set_detail_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if reaction_set_list_response_issues:
            print("api contract reaction set list response issues:", file=sys.stderr)
            for issue in reaction_set_list_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if document_response_issues:
            print("api contract document response issues:", file=sys.stderr)
            for issue in document_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if document_list_response_issues:
            print("api contract document list response issues:", file=sys.stderr)
            for issue in document_list_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if section_list_response_issues:
            print("api contract section list response issues:", file=sys.stderr)
            for issue in section_list_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if chunk_list_response_issues:
            print("api contract chunk list response issues:", file=sys.stderr)
            for issue in chunk_list_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if translation_response_issues:
            print("api contract translation response issues:", file=sys.stderr)
            for issue in translation_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if paper_detail_response_issues:
            print("api contract paper detail response issues:", file=sys.stderr)
            for issue in paper_detail_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if paper_mutation_response_issues:
            print("api contract paper mutation response issues:", file=sys.stderr)
            for issue in paper_mutation_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if paper_list_response_issues:
            print("api contract paper list response issues:", file=sys.stderr)
            for issue in paper_list_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if crawl_job_detail_response_issues:
            print("api contract crawl job detail response issues:", file=sys.stderr)
            for issue in crawl_job_detail_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if crawl_job_list_response_issues:
            print("api contract crawl job list response issues:", file=sys.stderr)
            for issue in crawl_job_list_response_issues:
                print(f"- {issue}", file=sys.stderr)
        if async_issues:
            print("api contract async response issues:", file=sys.stderr)
            for issue in async_issues:
                print(f"- {issue}", file=sys.stderr)
        if async_body_issues:
            print("api contract async response body issues:", file=sys.stderr)
            for issue in async_body_issues:
                print(f"- {issue}", file=sys.stderr)
        if empty_success_schema_issues:
            print("api contract empty success response schema issues:", file=sys.stderr)
            for issue in empty_success_schema_issues:
                print(f"- {issue}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
