import asyncio
from typing import Any, Optional
from urllib.parse import quote, urlparse

import httpx

from app.clients.retry_after import retry_after_delay


KNOWN_OA_STATUSES = {"gold", "green", "hybrid", "bronze", "closed", "unknown"}


class UnpaywallClient:
    base_url = "https://api.unpaywall.org/v2"

    def __init__(
        self,
        email: Optional[str],
        transport: Optional[Any] = None,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.25,
        request_interval_seconds: float = 0.0,
        timeout: float = 20.0,
        sleep: Any = asyncio.sleep,
    ):
        self.email = email
        self.transport = transport
        self.max_retries = max(1, max_retries)
        self.retry_backoff_seconds = retry_backoff_seconds
        self.request_interval_seconds = max(request_interval_seconds, 0.0)
        self.timeout = timeout
        self.sleep = sleep

    async def resolve(self, doi: str) -> dict[str, Any]:
        if not self.email:
            return {"oa_status": "unknown", "oa_pdf_url": None, "error": "UNPAYWALL_EMAIL is not configured"}
        headers = {"User-Agent": f"paper-lab-agent (mailto:{self.email})"}
        encoded_doi = quote(doi.strip(), safe="")
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers, transport=self.transport) as client:
            payload = await self._get_json(client, f"{self.base_url}/{encoded_doi}", {"email": self.email})
        if not isinstance(payload, dict):
            return {
                "oa_status": "unknown",
                "oa_pdf_url": None,
                "error": "Unpaywall response was not a JSON object",
            }
        return {
            "oa_status": oa_status(payload.get("oa_status")),
            "oa_pdf_url": payload_pdf_url(payload),
            "raw": payload,
        }

    async def _get_json(self, client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                await self.wait_after_successful_request()
                return payload
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if not self.should_retry_response(exc.response):
                    break
                if attempt < self.max_retries - 1:
                    await self.sleep(self.retry_delay(attempt, exc.response))
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    await self.sleep(self.retry_delay(attempt))
        raise RuntimeError(f"Unpaywall request failed: {last_error}")

    def should_retry_response(self, response: httpx.Response) -> bool:
        return response.status_code == 429 or response.status_code >= 500

    async def wait_after_successful_request(self) -> None:
        if self.request_interval_seconds > 0:
            await self.sleep(self.request_interval_seconds)

    def retry_delay(self, attempt: int, response: Optional[httpx.Response] = None) -> float:
        if response is not None and response.status_code == 429:
            parsed_delay = retry_after_delay(response)
            if parsed_delay is not None:
                return parsed_delay
        return self.retry_backoff_seconds * (attempt + 1)


def oa_status(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        normalized = value.strip().lower()
        if normalized in KNOWN_OA_STATUSES:
            return normalized
    return "unknown"


def payload_pdf_url(payload: dict[str, Any]) -> Optional[str]:
    pdf_url = best_pdf_url(payload.get("best_oa_location"))
    if pdf_url:
        return pdf_url
    locations = payload.get("oa_locations")
    if not isinstance(locations, list):
        return None
    for location in locations:
        pdf_url = best_pdf_url(location)
        if pdf_url:
            return pdf_url
    return None


def best_pdf_url(location: Any) -> Optional[str]:
    if not isinstance(location, dict):
        return None
    url_for_pdf = location.get("url_for_pdf")
    if url_for_pdf:
        pdf_url = web_url(url_for_pdf)
        if pdf_url:
            return pdf_url
    url = location.get("url")
    if not url:
        return None
    value = web_url(url)
    if not value:
        return None
    return value if urlparse(value).path.lower().endswith(".pdf") else None


def web_url(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value.strip()
