from pathlib import Path
from typing import Any, Optional

import requests

from app.release_readiness import RELEASE_BLOCKING_CONFIG_WARNING_CODES

ERROR_TEXT_LIMIT = 500


class FrontendApiError(RuntimeError):
    def __init__(self, status_code: int, payload: dict[str, Any]):
        self.status_code = status_code
        self.payload = payload
        super().__init__(format_error_payload(payload, status_code))


def normalize_base_url(base_url: str) -> str:
    return base_url.strip().rstrip("/")


def normalize_path(path: str) -> str:
    return f"/{path.lstrip('/')}"


def api_docs_links(base_url: str) -> dict[str, str]:
    root = normalize_base_url(base_url)
    if root.endswith("/api/v1"):
        root = root[: -len("/api/v1")]
    return {
        "OpenAPI JSON": f"{root}/openapi.json",
        "Swagger UI": f"{root}/docs",
        "ReDoc": f"{root}/redoc",
    }


def summarize_text(text: str, limit: int = ERROR_TEXT_LIMIT) -> str:
    value = " ".join((text or "").split())
    if len(value) <= limit:
        return value
    return f"{value[:limit].rstrip()}..."


def is_safe_download_file(path: Path) -> bool:
    try:
        for candidate in (path, *path.parents):
            if not candidate.is_symlink():
                continue
            if candidate.is_absolute() and candidate.parent == Path(candidate.anchor):
                continue
            return False
        return path.exists() and path.is_file()
    except OSError:
        return False


def response_payload(response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        text = summarize_text(getattr(response, "text", "") or "")
        message = text or "non-JSON response"
        return {"error": {"code": "http_error", "message": f"HTTP {response.status_code}: {message}"}}
    if isinstance(payload, dict):
        return payload
    return {"error": {"code": "invalid_response", "message": f"HTTP {response.status_code}: response must be a JSON object"}}


def format_error_payload(payload: dict[str, Any], status_code: Optional[int] = None) -> str:
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        code = error.get("code") or "api_error"
        message = error.get("message") or (f"HTTP {status_code}" if status_code is not None else "API error")
        return f"{code}: {message}"
    if status_code is not None:
        return f"HTTP {status_code}"
    return "API error"


def request_json_status(
    method: str,
    base_url: str,
    path: str,
    *,
    params: Optional[dict[str, Any]] = None,
    json: Any = None,
    files: Any = None,
    data: Any = None,
    timeout: float = 20,
) -> tuple[int, dict[str, Any]]:
    try:
        response = requests.request(
            method,
            f"{normalize_base_url(base_url)}{normalize_path(path)}",
            params=params,
            json=json,
            files=files,
            data=data,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        return 0, {"error": {"code": "request_failed", "message": str(exc) or exc.__class__.__name__}}
    payload = response_payload(response)
    if 200 <= response.status_code < 300 and "error" in payload:
        return 599, payload
    return response.status_code, payload


def request_json(
    method: str,
    base_url: str,
    path: str,
    *,
    params: Optional[dict[str, Any]] = None,
    json: Any = None,
    files: Any = None,
    data: Any = None,
    timeout: float = 20,
) -> dict[str, Any]:
    status_code, payload = request_json_status(
        method,
        base_url,
        path,
        params=params,
        json=json,
        files=files,
        data=data,
        timeout=timeout,
    )
    if status_code < 200 or status_code >= 300 or "error" in payload:
        raise FrontendApiError(status_code, payload)
    return payload


def compact_parts(parts: list[Any]) -> list[str]:
    return [str(part) for part in parts if part is not None and str(part) != ""]


def dataframe_display_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    display_rows = []
    for row in rows:
        if "value" not in row:
            display_rows.append(row)
            continue
        value = row.get("value")
        display_rows.append({**row, "value": "" if value is None else str(value)})
    return display_rows


def release_readiness_display_state(release_readiness: Any) -> dict[str, Any]:
    if not isinstance(release_readiness, dict):
        invalid_group = {"label": "release state:", "items": ["release_readiness:invalid"]}
        return {
            "ready": False,
            "blockers": ["release_readiness:invalid"],
            "groups": [invalid_group],
        }
    config_warning_codes = release_readiness_list_values(
        release_readiness.get("config_warning_codes"), invalid_label="invalid"
    )
    blocking_config_warnings = [
        f"config_warning_codes:{code}"
        for code in config_warning_codes
        if code == "invalid" or code in RELEASE_BLOCKING_CONFIG_WARNING_CODES
    ]
    groups = [
        {
            "label": "demo data missing:",
            "items": release_readiness_list_values(release_readiness.get("demo_data_missing"), invalid_label="invalid"),
        },
        {
            "label": "failed workflows:",
            "items": release_readiness_list_values(release_readiness.get("failed_workflows"), invalid_label="invalid"),
        },
        {
            "label": "config warnings:",
            "items": blocking_config_warnings,
        },
        {
            "label": "storage errors:",
            "items": release_readiness_list_values(release_readiness.get("storage_errors"), invalid_label="invalid"),
        },
    ]
    blockers = [item for group in groups for item in group["items"]]
    if not blockers and release_readiness.get("ready") is not True:
        groups.append({"label": "release state:", "items": ["ready=false"]})
        blockers = ["ready=false"]
    return {
        "ready": release_readiness.get("ready") is True and not blockers,
        "blockers": blockers,
        "groups": groups,
    }


def release_readiness_list_values(value: Any, invalid_label: Optional[str] = None) -> list[str]:
    if not isinstance(value, list):
        return [invalid_label] if invalid_label is not None else []
    values: list[str] = []
    invalid = False
    for item in value:
        if isinstance(item, str) and item.strip():
            values.append(item)
        else:
            invalid = True
    if invalid and invalid_label is not None:
        values.append(invalid_label)
    return values


def demo_data_display_state(demo_data: Any) -> dict[str, Any]:
    if not isinstance(demo_data, dict):
        return {"ready": False, "missing": ["demo_data:invalid"]}
    missing = release_readiness_list_values(demo_data.get("missing"), invalid_label="invalid")
    if missing:
        return {"ready": False, "missing": missing}
    if demo_data.get("ready") is True:
        return {"ready": True, "missing": []}
    return {"ready": False, "missing": ["ready=false"]}


SYSTEM_COUNT_METRICS = [
    ("期刊", "journals"),
    ("论文", "papers"),
    ("文档", "documents"),
]


def system_count_metric_rows(counts: Any) -> list[dict[str, Any]]:
    if not isinstance(counts, dict):
        return [{"label": "系统计数", "value": "invalid", "warning": "counts: invalid"}]
    rows: list[dict[str, Any]] = []
    for label, key in SYSTEM_COUNT_METRICS:
        value = counts.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            rows.append({"label": label, "value": "invalid", "warning": f"counts.{key}: invalid"})
            continue
        rows.append({"label": label, "value": value, "warning": None})
    return rows


def runtime_status_rows(runtime: Any) -> list[dict[str, str]]:
    if not isinstance(runtime, dict):
        return [{"kind": "warning", "text": "runtime: invalid"}]
    rows: list[dict[str, str]] = []
    api_prefix = runtime.get("api_prefix")
    if isinstance(api_prefix, str) and api_prefix.strip():
        rows.append({"kind": "caption", "text": f"API: {api_prefix}"})
    else:
        rows.append({"kind": "warning", "text": "api_prefix: invalid"})
    version = runtime.get("version")
    if isinstance(version, str) and version.strip():
        rows.append({"kind": "caption", "text": f"version: {version}"})
    else:
        rows.append({"kind": "warning", "text": "version: invalid"})
    scheduler_enabled = runtime.get("scheduler_enabled")
    if isinstance(scheduler_enabled, bool):
        rows.append({"kind": "caption", "text": f"scheduler_enabled: {scheduler_enabled}"})
    else:
        rows.append({"kind": "warning", "text": "scheduler_enabled: invalid"})
    scheduler_jobs = runtime.get("scheduler_jobs") or []
    if not isinstance(scheduler_jobs, list):
        return [*rows, {"kind": "warning", "text": "scheduler_jobs: invalid"}]
    if scheduler_jobs:
        rows.append({"kind": "caption", "text": "scheduler_jobs:"})
    for job in scheduler_jobs:
        if not isinstance(job, dict):
            rows.append({"kind": "warning", "text": "scheduler_jobs: invalid"})
            continue
        period = job.get("period")
        job_id = job.get("id")
        schedule = job.get("schedule")
        timezone = job.get("timezone")
        if not all(isinstance(value, str) and value.strip() for value in (period, job_id, schedule, timezone)):
            rows.append({"kind": "warning", "text": "scheduler_jobs: invalid"})
            continue
        rows.append(
            {
                "kind": "caption",
                "text": f"- {period} · {job_id} · {schedule} {timezone}",
            }
        )
    return rows


def database_path_status_row(database_path: Any) -> dict[str, str]:
    if not isinstance(database_path, str) or not database_path.strip():
        return {"kind": "warning", "text": "database_path: invalid"}
    return {"kind": "caption", "text": f"DB: {database_path}"}


STORAGE_HEALTH_DISPLAY_KEYS = [
    "data_dir",
    "pdf_dir",
    "tei_dir",
    "translation_dir",
    "export_dir",
    "database",
    "database_parent",
    "vector_db_parent",
    "vector_db",
]


def storage_health_caption_rows(storage_health: Any) -> list[dict[str, str]]:
    if not isinstance(storage_health, dict):
        return [{"kind": "warning", "text": "storage_health: invalid"}]
    rows = []
    for key in STORAGE_HEALTH_DISPLAY_KEYS:
        health_entry = storage_health.get(key) or {}
        if not isinstance(health_entry, dict):
            rows.append({"kind": "warning", "text": f"{key}: invalid"})
            health_entry = {}
        exists_label = "exists" if health_entry.get("exists") else "missing"
        writable_label = "writable" if health_entry.get("writable") else "not writable"
        rows.append(
            {
                "kind": "caption",
                "text": f"{key}: {exists_label} · {writable_label} · {health_entry.get('path') or '-'}",
            }
        )
        if key == "vector_db":
            valid_json = health_entry.get("valid_json")
            valid_json_label = "unchecked" if valid_json is None else ("valid_json" if valid_json else "invalid_json")
            rows.append({"kind": "caption", "text": f"vector_db valid_json: {valid_json_label}"})
        if health_entry.get("error"):
            rows.append({"kind": "warning", "text": f"{key} error: {health_entry['error']}"})
    return rows


def external_capabilities_display_state(external_capabilities: Any) -> dict[str, Any]:
    if not isinstance(external_capabilities, dict):
        return {
            "capabilities": {},
            "grobid": {},
            "warnings": ["external_capabilities:invalid"],
        }
    warnings: list[str] = []
    grobid = external_capabilities.get("grobid") or {}
    if not isinstance(grobid, dict):
        grobid = {}
        warnings.append("grobid:invalid")
    return {
        "capabilities": external_capabilities,
        "grobid": grobid,
        "warnings": warnings,
    }


WORKFLOW_STATUS_COUNT_KEYS = [
    "crawl_jobs",
    "document_parse",
    "document_index",
    "document_chemistry",
    "translations",
    "reaction_sets",
]


def status_count_rows(status_counts: Any) -> list[dict[str, Any]]:
    if not isinstance(status_counts, dict):
        return [{"workflow": "status_counts", "status": "invalid", "count": 1}]
    rows: list[dict[str, Any]] = []
    for workflow in WORKFLOW_STATUS_COUNT_KEYS:
        workflow_counts = status_counts.get(workflow) or {}
        if not isinstance(workflow_counts, dict):
            rows.append({"workflow": workflow, "status": "invalid", "count": 1})
            continue
        rows.extend(
            {"workflow": workflow, "status": state, "count": count}
            for state, count in workflow_counts.items()
        )
    return rows


def config_warning_rows(config_warnings: Any) -> list[dict[str, str]]:
    if not isinstance(config_warnings, list):
        return [{"capability": "config_warnings", "message": "invalid"}]
    rows: list[dict[str, str]] = []
    for warning in config_warnings:
        if not isinstance(warning, dict):
            rows.append({"capability": "config_warnings", "message": "invalid"})
            continue
        capability = warning.get("capability") or "unknown"
        message = warning.get("message") or warning.get("code") or "configuration warning"
        rows.append({"capability": str(capability), "message": str(message)})
    return rows


def crawl_journal_options(journals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    options = [{"label": "全部 active 期刊", "journal_id": None}]
    for journal in journals:
        issn_label = " / ".join(compact_parts([journal.get("issn_print"), journal.get("issn_electronic")]))
        suffix = f" · {issn_label}" if issn_label else ""
        options.append({"label": f"#{journal['id']} · {journal['name']}{suffix}", "journal_id": journal["id"]})
    return options


def crawl_journal_option_label(option: dict[str, Any]) -> str:
    return str(option.get("label") or "期刊选项")


def journal_option_label(journal: dict[str, Any]) -> str:
    return f"#{journal['id']} {journal.get('name') or 'Journal'} · active={bool(journal.get('active'))}"


def category_parent_option_label(category: Optional[dict[str, Any]]) -> str:
    if category is None:
        return "无"
    return f"#{category['id']} {category.get('slug') or 'category'}"


def paper_category_option_label(category: dict[str, Any]) -> str:
    return f"{category.get('slug') or 'category'} · {category.get('name') or 'category'}"


def paper_upload_option_label(paper: Optional[dict[str, Any]]) -> str:
    if paper is None:
        return "不关联论文"
    return (
        f"#{paper.get('id')} · {paper.get('title') or 'Untitled'} · "
        f"DOI: {paper.get('doi') or '-'} · "
        f"{paper.get('journal_name') or '-'} · "
        f"{paper.get('published_date') or '-'}"
    )


def paper_upload_query_params(query: Optional[str]) -> dict[str, Any]:
    params: dict[str, Any] = {"page": 1, "page_size": 100}
    normalized = (query or "").strip()
    if normalized:
        params["q"] = normalized
    return params


DOCUMENT_STATUS_FILTERS: dict[str, Optional[tuple[str, str]]] = {
    "全部": None,
    "待解析": ("parse_status", "uploaded"),
    "解析中": ("parse_status", "parsing"),
    "解析失败": ("parse_status", "failed"),
    "待索引": ("index_status", "not_indexed"),
    "索引中": ("index_status", "indexing"),
    "索引失败": ("index_status", "failed"),
    "待抽取": ("chemistry_status", "not_extracted"),
    "抽取中": ("chemistry_status", "extracting"),
    "抽取失败": ("chemistry_status", "failed"),
    "抽取被拒绝": ("chemistry_status", "rejected"),
}


def document_status_filter_options() -> list[str]:
    return list(DOCUMENT_STATUS_FILTERS)


def filter_documents_by_status(documents: list[dict[str, Any]], filter_value: str) -> list[dict[str, Any]]:
    condition = DOCUMENT_STATUS_FILTERS.get(filter_value)
    if condition is None:
        return list(documents)
    field, expected = condition
    return [document for document in documents if document.get(field) == expected]


def document_filter_summary(total_count: int, filtered_count: int, filter_value: str) -> str:
    return f"当前页匹配 {filtered_count}/{total_count} · 筛选: {filter_value}"


def crawl_job_rows(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for job in jobs:
        diagnostics = job.get("diagnostics") or {}
        journal = job.get("journal") or {}
        status = diagnostics.get("status") or job.get("status")
        error = diagnostics.get("error") or job.get("error")
        found = int(diagnostics.get("papers_found") or 0)
        accepted = int(diagnostics.get("papers_accepted") or 0)
        new = int(diagnostics.get("papers_new") or 0)
        rows.append(
            {
                "id": job.get("id") or job.get("job_id"),
                "journal": journal.get("name") or diagnostics.get("journal_name") or job.get("journal_id"),
                "status": status,
                "workflow_state": f"failed: {error}" if status == "failed" and error else str(status or "unknown"),
                "period": diagnostics.get("period") or job.get("period"),
                "date_from": diagnostics.get("date_from") or job.get("date_from"),
                "date_to": diagnostics.get("date_to") or job.get("date_to"),
                "found": found,
                "filtered": int(diagnostics.get("papers_filtered") or 0),
                "accepted": accepted,
                "existing": int(diagnostics.get("papers_existing") or 0),
                "new": new,
                "progress_summary": f"{found} found / {accepted} accepted / {new} new",
                "outcome": diagnostics.get("outcome"),
                "keyword_mode": diagnostics.get("keyword_mode"),
                "keyword_terms": ", ".join(diagnostics.get("keyword_terms") or []),
                "error": error,
            }
        )
    return rows


def crawl_job_option_label(job: dict[str, Any]) -> str:
    return (
        f"#{job.get('id') or job.get('job_id')} · "
        f"journal {job.get('journal_id') or '-'} · "
        f"{job.get('status') or 'unknown'}"
    )


def crawl_job_diagnostic_rows(job: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics = job.get("diagnostics") or {}
    journal = job.get("journal") or {}
    fields = [
        ("job_id", job.get("id") or job.get("job_id")),
        ("status", diagnostics.get("status") or job.get("status")),
        ("journal", journal.get("name") or diagnostics.get("journal_name") or job.get("journal_id")),
        ("period", diagnostics.get("period") or job.get("period")),
        ("date_from", diagnostics.get("date_from") or job.get("date_from")),
        ("date_to", diagnostics.get("date_to") or job.get("date_to")),
        ("papers_found", int(diagnostics.get("papers_found") or 0)),
        ("papers_filtered", int(diagnostics.get("papers_filtered") or 0)),
        ("papers_accepted", int(diagnostics.get("papers_accepted") or 0)),
        ("papers_existing", int(diagnostics.get("papers_existing") or 0)),
        ("papers_new", int(diagnostics.get("papers_new") or 0)),
        ("outcome", diagnostics.get("outcome")),
        ("keyword_mode", diagnostics.get("keyword_mode")),
        ("keyword_terms", ", ".join(diagnostics.get("keyword_terms") or [])),
        ("error", diagnostics.get("error") or job.get("error")),
    ]
    return [{"field": field, "value": value} for field, value in fields]


def document_option_label(document: dict[str, Any]) -> str:
    file_path = str(document.get("file_path") or "")
    file_name = document.get("original_name") or file_path.rsplit("/", 1)[-1] or "document"
    paper = document.get("paper") if isinstance(document.get("paper"), dict) else {}
    paper_parts = compact_parts(
        [
            paper.get("title"),
            f"DOI: {paper.get('doi')}" if paper.get("doi") else None,
        ]
    )
    paper_suffix = f" · {' · '.join(paper_parts)}" if paper_parts else ""
    parse_status = document.get("parse_status") or "unknown"
    index_status = document.get("index_status") or "unknown"
    chemistry_status = document.get("chemistry_status") or "unknown"
    return (
        f"#{document.get('id')} · {file_name}{paper_suffix} · "
        f"parse={parse_status} · index={index_status} · chemistry={chemistry_status}"
    )


def document_status_rows(document: dict[str, Any], chunks: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    chunks = chunks or {}
    index_status = chunks.get("index_status") or document.get("index_status") or "unknown"
    index_error = chunks.get("index_error") or document.get("index_error")
    rows = [
        ("document_id", document.get("id")),
        ("parse_status", document.get("parse_status") or "unknown"),
        ("parse_error", document.get("parse_error")),
        ("index_status", index_status),
        ("index_error", index_error),
        ("chunks_total", int(chunks.get("total") or 0)),
        ("chemistry_status", document.get("chemistry_status") or "unknown"),
        ("chemistry_error", document.get("chemistry_error")),
    ]
    return [{"field": field, "value": value} for field, value in rows]


def document_asset_downloads(document: dict[str, Any]) -> list[dict[str, Any]]:
    assets = [
        ("pdf", "file_path", "下载原始 PDF", "application/pdf", "PDF 文件不存在", "bytes"),
        ("tei", "tei_path", "下载 TEI XML", "application/xml", "TEI 文件不存在", "text"),
    ]
    downloads = []
    for kind, field, label, mime, missing_label, data_mode in assets:
        raw_path = document.get(field)
        if not isinstance(raw_path, str) or not raw_path:
            continue
        path = Path(raw_path)
        exists = is_safe_download_file(path)
        data = None
        if exists:
            try:
                data = path.read_bytes() if data_mode == "bytes" else path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                exists = False
        downloads.append(
            {
                "kind": kind,
                "label": label,
                "data": data,
                "file_name": path.name,
                "mime": mime,
                "path": str(path),
                "exists": exists,
                "missing_message": None if exists else f"{missing_label}: {path}",
            }
        )
    return downloads


def document_section_rows(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for section in sections:
        section_id = section.get("id")
        section_seq = section.get("seq")
        section_ref = section_seq if section_seq is not None else section_id
        content = section.get("content") or ""
        section_location = " · ".join(
            compact_parts(
                [
                    f"section {section_ref}" if section_ref is not None else None,
                    section.get("section_type"),
                    section.get("title"),
                ]
            )
        )
        rows.append(
            {
                "id": section_id,
                "document_id": section.get("document_id"),
                "seq": section_seq,
                "section_type": section.get("section_type"),
                "title": section.get("title"),
                "section_location": section_location or "-",
                "content_preview": summarize_text(content, limit=160),
                "content_chars": len(content),
            }
        )
    return rows


def document_section_option_label(section: dict[str, Any]) -> str:
    section_ref = section.get("seq") if section.get("seq") is not None else section.get("id")
    label = section.get("title") or section.get("section_type") or "section"
    return f"{section_ref}. {label}"


def translation_status_rows(
    translation: dict[str, Any], *, preview_text: Optional[str] = None
) -> list[dict[str, Any]]:
    preview = preview_text or ""
    rows = [
        ("document_id", translation.get("document_id")),
        ("status", translation.get("status") or "unknown"),
        ("target_lang", translation.get("target_lang")),
        ("output_path", translation.get("output_path")),
        ("error", translation.get("error")),
        ("preview_chars", len(preview)),
        ("preview", summarize_text(preview, limit=160)),
    ]
    return [{"field": field, "value": value} for field, value in rows]


def translation_download(translation: dict[str, Any]) -> Optional[dict[str, Any]]:
    output_path = translation.get("output_path")
    if not isinstance(output_path, str) or not output_path:
        return None
    path = Path(output_path)
    if not is_safe_download_file(path):
        return None
    try:
        data = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    return {
        "label": "下载双语翻译",
        "data": data,
        "file_name": path.name,
        "mime": "text/markdown",
        "path": str(path),
    }


def document_chunk_rows(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for chunk in chunks:
        section_id = chunk.get("section_id")
        section_seq = chunk.get("section_seq")
        section_ref = section_seq if section_seq is not None else section_id
        text = chunk.get("text") or ""
        chunk_location = " · ".join(
            compact_parts(
                [
                    f"section {section_ref}" if section_ref is not None else None,
                    chunk.get("section_title"),
                    f"vector {chunk.get('vector_id')}" if chunk.get("vector_id") else None,
                ]
            )
        )
        rows.append(
            {
                "id": chunk.get("id"),
                "document_id": chunk.get("document_id"),
                "section_id": section_id,
                "section_seq": section_seq,
                "section_title": chunk.get("section_title"),
                "vector_id": chunk.get("vector_id"),
                "chunk_location": chunk_location or "-",
                "text_preview": summarize_text(text, limit=160),
                "text_chars": len(text),
            }
        )
    return rows


def document_chunk_option_label(chunk: dict[str, Any]) -> str:
    chunk_ref = chunk.get("vector_id") or chunk.get("id")
    return f"{chunk_ref} · {chunk.get('section_title') or '-'}"


def rag_source_rows(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for source in sources:
        paper_id = source.get("paper_id")
        document_id = source.get("document_id")
        section_seq = source.get("section_seq")
        section_id = source.get("section_id")
        section_ref = section_seq if section_seq is not None else section_id
        chunk_id = source.get("chunk_id")
        citation = " · ".join(
            compact_parts(
                [
                    f"paper {paper_id}" if paper_id is not None else None,
                    f"doc {document_id}" if document_id is not None else None,
                    f"section {section_ref}" if section_ref is not None else None,
                    f"chunk {chunk_id}" if chunk_id is not None else None,
                ]
            )
        )
        source_location = " · ".join(
            compact_parts(
                [
                    f"paper {paper_id}" if paper_id is not None else None,
                    f"doc {document_id}" if document_id is not None else None,
                    f"section {section_ref}" if section_ref is not None else None,
                    source.get("section_type"),
                    source.get("section_title"),
                ]
            )
        )
        rows.append(
            {
                "citation": f"[{citation}]" if citation else "[-]",
                "source_location": source_location or "-",
                "document_id": document_id,
                "paper_id": paper_id,
                "paper_title": source.get("paper_title"),
                "section_id": section_id,
                "section_seq": section_seq,
                "section_title": source.get("section_title"),
                "section_type": source.get("section_type"),
                "source_excerpt": source.get("source_excerpt"),
                "chunk_id": chunk_id,
                "vector_id": source.get("vector_id"),
                "score": source.get("score"),
            }
        )
    return rows


def rag_source_option_label(source: dict[str, Any]) -> str:
    label = " · ".join(compact_parts([source.get("citation"), source.get("source_location")]))
    return label or "引用来源"


def reaction_set_rows(reaction_sets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in reaction_sets:
        reaction_count = int(item.get("reaction_count") or 0)
        verified_count = int(item.get("verified_count") or 0)
        unverified_count = int(item.get("unverified_count") or 0)
        export_ready = bool(item.get("export_ready"))
        if reaction_count == 0:
            export_state = "empty"
        elif export_ready:
            export_state = "ready"
        else:
            export_state = f"blocked: {unverified_count} unverified"
        rows.append(
            {
                "id": item.get("id"),
                "document_id": item.get("document_id"),
                "name": item.get("name"),
                "status": item.get("status"),
                "reaction_count": reaction_count,
                "verified_count": verified_count,
                "unverified_count": unverified_count,
                "export_ready": export_ready,
                "export_state": export_state,
                "review_progress": f"{verified_count}/{reaction_count} verified",
                "verified_by": item.get("verified_by"),
                "verified_at": item.get("verified_at"),
            }
        )
    return rows


def reaction_display_state(reaction: dict[str, Any]) -> dict[str, Any]:
    source_section_seq = reaction.get("source_section_seq")
    source_summary = (
        f"verified: {bool(reaction.get('verified'))} · "
        f"confidence: {reaction.get('confidence')} · "
        f"source_section_id: {reaction.get('source_section_id')} · "
        f"source_section_title: {reaction.get('source_section_title') or '-'} · "
        f"source_section_type: {reaction.get('source_section_type') or '-'} · "
        f"source_section_seq: {source_section_seq if source_section_seq is not None else '-'} · "
        f"source_label: {reaction.get('source_label') or '-'}"
    )
    species_summary = (
        f"reactants: {reaction.get('reactants') or '-'} · "
        f"products: {reaction.get('products') or '-'} · "
        f"reference: {reaction.get('reference') or '-'}"
    )
    return {
        "reaction": reaction.get("reaction"),
        "source_excerpt": reaction.get("source_excerpt"),
        "source_summary": source_summary,
        "species_summary": species_summary,
    }


def reaction_set_option_label(item: dict[str, Any]) -> str:
    document_part = f"doc {item.get('document_id')} · " if item.get("document_id") is not None else ""
    return (
        f"#{item['id']} · {document_part}{item.get('status') or 'unknown'} · "
        f"export_ready {bool(item.get('export_ready'))} · "
        f"未复核 {item.get('unverified_count', 0)} · {item.get('name') or 'Reaction set'}"
    )


def normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


REACTION_TYPE_OPTIONS = ["", "elastic", "excitation", "ionization", "attachment", "recombination"]
RATE_TYPE_OPTIONS = ["", "cross_section", "arrhenius", "constant"]


def option_index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def normalized_option_value(value: Any) -> str:
    normalized = str(value or "")
    return "" if normalized == "unknown" else normalized


def reaction_review_form_state(reaction: dict[str, Any]) -> dict[str, Any]:
    reaction_type_value = normalized_option_value(reaction.get("reaction_type"))
    rate_type_value = normalized_option_value(reaction.get("rate_type"))
    include_threshold_ev = reaction.get("threshold_ev") is not None
    threshold_ev_value = float(reaction["threshold_ev"]) if include_threshold_ev else 0.0
    return {
        "reaction_type_options": REACTION_TYPE_OPTIONS,
        "rate_type_options": RATE_TYPE_OPTIONS,
        "reaction_type_value": reaction_type_value,
        "reaction_type_index": option_index(REACTION_TYPE_OPTIONS, reaction_type_value),
        "rate_type_value": rate_type_value,
        "rate_type_index": option_index(RATE_TYPE_OPTIONS, rate_type_value),
        "include_threshold_ev": include_threshold_ev,
        "threshold_ev_value": threshold_ev_value,
        "rate_value": reaction.get("rate_value") or "",
        "cross_section_url": reaction.get("cross_section_url") or "",
        "verified": bool(reaction.get("verified")),
        "verified_by": "streamlit",
    }


def reaction_review_payload(
    *,
    verified: bool,
    reaction_type: Optional[str],
    rate_type: Optional[str],
    rate_value: Optional[str],
    include_threshold_ev: bool,
    threshold_ev: Optional[float],
    cross_section_url: Optional[str],
    verified_by: Optional[str],
) -> dict[str, Any]:
    return {
        "verified": bool(verified),
        "reaction_type": normalize_optional_text(reaction_type),
        "rate_type": normalize_optional_text(rate_type),
        "rate_value": normalize_optional_text(rate_value),
        "threshold_ev": threshold_ev if include_threshold_ev else None,
        "cross_section_url": normalize_optional_text(cross_section_url),
        "verified_by": normalize_optional_text(verified_by),
    }


def reaction_export_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    export_format = payload.get("format") or "unknown"
    reaction_count = int(payload.get("reaction_count") or 0)
    audit_entry_count = int(payload.get("audit_entry_count") or 0)
    rows = [
        ("reaction_set_id", payload.get("reaction_set_id")),
        ("format", export_format),
        ("output_path", payload.get("output_path")),
        ("mime_type", payload.get("mime_type")),
        ("reaction_count", reaction_count),
        ("audit_entry_count", audit_entry_count),
        ("download_label", f"{export_format} · {reaction_count} reactions · {audit_entry_count} audit entries"),
    ]
    return [{"field": field, "value": value} for field, value in rows]


def reaction_export_download(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    output_path = payload.get("output_path")
    if not isinstance(output_path, str) or not output_path:
        return None
    path = Path(output_path)
    if not is_safe_download_file(path):
        return None
    mime = payload.get("mime_type") or "application/octet-stream"
    try:
        data = (
            path.read_text(encoding="utf-8")
            if mime.startswith("text/") or mime == "application/json"
            else path.read_bytes()
        )
    except (OSError, UnicodeError):
        return None
    return {
        "label": "下载导出文件",
        "data": data,
        "file_name": path.name,
        "mime": mime,
        "path": str(path),
    }


def int_or_default(value: Any, default: int) -> int:
    return default if value is None else int(value)


def reaction_set_review_state(detail: dict[str, Any]) -> dict[str, Any]:
    reactions = detail.get("reactions") or []
    unverified_reactions = [reaction for reaction in reactions if not reaction.get("verified")]
    reaction_count = int_or_default(detail.get("reaction_count"), len(reactions))
    verified_count = int_or_default(detail.get("verified_count"), reaction_count - len(unverified_reactions))
    unverified_count = int_or_default(detail.get("unverified_count"), len(unverified_reactions))
    export_ready_value = detail.get("export_ready")
    export_ready = bool(export_ready_value) if export_ready_value is not None else reaction_count > 0 and unverified_count == 0
    export_blocked = not export_ready
    if reaction_count == 0:
        export_message = "没有可导出的反应。"
    elif export_blocked:
        export_message = "未全复核不可导出：请先完成所有反应复核。"
    else:
        export_message = None
    summary = (
        f"status: {detail.get('status')} · "
        f"reactions: {reaction_count} · "
        f"verified: {verified_count} · "
        f"未复核: {unverified_count} · "
        f"export_ready: {export_ready} · "
        f"gas_mixture: {detail.get('gas_mixture') or '-'} · "
        f"lxcat_db: {detail.get('lxcat_db') or '-'} · "
        f"verified_by: {detail.get('verified_by') or '-'} · "
        f"verified_at: {detail.get('verified_at') or '-'}"
    )
    return {
        "reactions": reactions,
        "unverified_reactions": unverified_reactions,
        "reaction_count": reaction_count,
        "verified_count": verified_count,
        "unverified_count": unverified_count,
        "export_ready": export_ready,
        "export_blocked": export_blocked,
        "export_message": export_message,
        "source_note": detail.get("source_note"),
        "summary": summary,
    }


def reaction_audit_rows(audit_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for audit in audit_log:
        field_changes = audit.get("field_changes") or {}
        if not field_changes:
            rows.append(
                {
                    "audit_id": audit.get("id"),
                    "reaction_id": audit.get("reaction_id"),
                    "field": "-",
                    "before": "",
                    "after": "",
                    "verified_by": audit.get("verified_by"),
                    "verified_at": audit.get("verified_at"),
                }
            )
            continue
        for field, change in field_changes.items():
            rows.append(
                {
                    "audit_id": audit.get("id"),
                    "reaction_id": audit.get("reaction_id"),
                    "field": field,
                    "before": audit_cell_text(change.get("before")),
                    "after": audit_cell_text(change.get("after")),
                    "verified_by": audit.get("verified_by"),
                    "verified_at": audit.get("verified_at"),
                }
            )
    return rows


def audit_cell_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def reaction_review_list_state(reactions: list[dict[str, Any]], *, only_unverified: bool = False) -> dict[str, Any]:
    unverified_reactions = [reaction for reaction in reactions if not reaction.get("verified")]
    if only_unverified:
        display_reactions = unverified_reactions
        hidden_verified_count = len(reactions) - len(unverified_reactions)
        summary = f"当前显示未复核: {len(display_reactions)}/{len(reactions)} · 已隐藏已复核: {hidden_verified_count}"
        mode = "unverified"
    else:
        display_reactions = reactions
        summary = f"当前显示全部反应: {len(display_reactions)} · 未复核: {len(unverified_reactions)}"
        mode = "all"
    return {
        "display_reactions": display_reactions,
        "total_count": len(reactions),
        "display_count": len(display_reactions),
        "unverified_count": len(unverified_reactions),
        "mode": mode,
        "summary": summary,
    }


def reaction_review_rows(reactions: list[dict[str, Any]], *, only_unverified: bool = False) -> list[dict[str, Any]]:
    rows = []
    for reaction in reactions:
        verified = bool(reaction.get("verified"))
        if only_unverified and verified:
            continue
        section_ref = (
            reaction.get("source_section_seq")
            if reaction.get("source_section_seq") is not None
            else reaction.get("source_section_id")
        )
        source_section = " | ".join(
            str(part)
            for part in [
                reaction.get("source_section_seq"),
                reaction.get("source_section_type"),
                reaction.get("source_section_title"),
            ]
            if part is not None and part != ""
        )
        source_location = " · ".join(
            compact_parts(
                [
                    f"section {section_ref}" if section_ref is not None else None,
                    reaction.get("source_section_type"),
                    reaction.get("source_section_title"),
                ]
            )
        )
        rows.append(
            {
                "id": reaction.get("id"),
                "verified": verified,
                "review_state": "verified" if verified else "unverified",
                "export_blocker": None if verified else "unverified reaction",
                "reaction": reaction.get("reaction"),
                "confidence": reaction.get("confidence"),
                "reaction_type": reaction.get("reaction_type"),
                "rate_type": reaction.get("rate_type"),
                "rate_value": reaction.get("rate_value"),
                "threshold_ev": reaction.get("threshold_ev"),
                "cross_section_url": reaction.get("cross_section_url"),
                "source_section": source_section or "-",
                "source_location": source_location or "-",
                "source_section_id": reaction.get("source_section_id"),
                "source_label": reaction.get("source_label"),
                "source_excerpt": reaction.get("source_excerpt"),
            }
        )
    return rows
