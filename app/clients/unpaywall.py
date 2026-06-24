import asyncio
from typing import Any, Optional
from urllib.parse import urlparse

import httpx


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
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            payload = await self._get_json(client, f"{self.base_url}/{doi}", {"email": self.email})
        if not isinstance(payload, dict):
            return {
                "oa_status": "unknown",
                "oa_pdf_url": None,
                "error": "Unpaywall response was not a JSON object",
            }
        best = payload.get("best_oa_location") or {}
        return {
            "oa_status": payload.get("oa_status") or "unknown",
            "oa_pdf_url": best_pdf_url(best),
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
                if attempt < self.max_retries - 1:
                    await self.sleep(self.retry_delay(attempt, exc.response))
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    await self.sleep(self.retry_delay(attempt))
        raise RuntimeError(f"Unpaywall request failed: {last_error}")

    async def wait_after_successful_request(self) -> None:
        if self.request_interval_seconds > 0:
            await self.sleep(self.request_interval_seconds)

    def retry_delay(self, attempt: int, response: Optional[httpx.Response] = None) -> float:
        if response is not None and response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(float(retry_after), 0.0)
                except ValueError:
                    pass
        return self.retry_backoff_seconds * (attempt + 1)


def best_pdf_url(location: Any) -> Optional[str]:
    if not isinstance(location, dict):
        return None
    url_for_pdf = location.get("url_for_pdf")
    if url_for_pdf:
        return url_for_pdf
    url = location.get("url")
    if not url:
        return None
    path = urlparse(str(url)).path.lower()
    return str(url) if path.endswith(".pdf") else None
