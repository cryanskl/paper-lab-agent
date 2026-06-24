from typing import Any, Optional

import requests


class FrontendApiError(RuntimeError):
    def __init__(self, status_code: int, payload: dict[str, Any]):
        self.status_code = status_code
        self.payload = payload
        super().__init__(format_error_payload(payload, status_code))


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def response_payload(response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        text = (getattr(response, "text", "") or "").strip()
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
            f"{normalize_base_url(base_url)}{path}",
            params=params,
            json=json,
            files=files,
            data=data,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        return 0, {"error": {"code": "request_failed", "message": str(exc) or exc.__class__.__name__}}
    return response.status_code, response_payload(response)


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
