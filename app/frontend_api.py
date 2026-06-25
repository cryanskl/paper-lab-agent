from typing import Any, Optional

import requests


ERROR_TEXT_LIMIT = 500


class FrontendApiError(RuntimeError):
    def __init__(self, status_code: int, payload: dict[str, Any]):
        self.status_code = status_code
        self.payload = payload
        super().__init__(format_error_payload(payload, status_code))


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def normalize_path(path: str) -> str:
    return f"/{path.lstrip('/')}"


def summarize_text(text: str, limit: int = ERROR_TEXT_LIMIT) -> str:
    value = " ".join((text or "").split())
    if len(value) <= limit:
        return value
    return f"{value[:limit].rstrip()}..."


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


def reaction_review_rows(reactions: list[dict[str, Any]], *, only_unverified: bool = False) -> list[dict[str, Any]]:
    rows = []
    for reaction in reactions:
        verified = bool(reaction.get("verified"))
        if only_unverified and verified:
            continue
        source_section = " | ".join(
            str(part)
            for part in [
                reaction.get("source_section_seq"),
                reaction.get("source_section_type"),
                reaction.get("source_section_title"),
            ]
            if part is not None and part != ""
        )
        rows.append(
            {
                "id": reaction.get("id"),
                "verified": verified,
                "reaction": reaction.get("reaction"),
                "confidence": reaction.get("confidence"),
                "reaction_type": reaction.get("reaction_type"),
                "rate_type": reaction.get("rate_type"),
                "rate_value": reaction.get("rate_value"),
                "threshold_ev": reaction.get("threshold_ev"),
                "cross_section_url": reaction.get("cross_section_url"),
                "source_section": source_section or "-",
                "source_section_id": reaction.get("source_section_id"),
                "source_label": reaction.get("source_label"),
                "source_excerpt": reaction.get("source_excerpt"),
            }
        )
    return rows
