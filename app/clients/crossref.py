import asyncio
import html
import re
from typing import Any, Optional

import httpx


class CrossrefClient:
    base_url = "https://api.crossref.org"

    def __init__(
        self,
        mailto: Optional[str] = None,
        transport: Optional[Any] = None,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.25,
        request_interval_seconds: float = 0.0,
        timeout: float = 20.0,
        sleep: Any = asyncio.sleep,
    ):
        self.mailto = mailto
        self.transport = transport
        self.max_retries = max(1, max_retries)
        self.retry_backoff_seconds = retry_backoff_seconds
        self.request_interval_seconds = max(request_interval_seconds, 0.0)
        self.timeout = timeout
        self.sleep = sleep

    async def works_by_issn(self, issn: str, date_from: str, date_to: str, max_pages: int = 3) -> list[dict[str, Any]]:
        headers = {}
        if self.mailto:
            headers["User-Agent"] = f"paper-lab-agent (mailto:{self.mailto})"
        params = {
            "filter": f"from-pub-date:{date_from},until-pub-date:{date_to}",
            "rows": 100,
            "cursor": "*",
        }
        results: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers, transport=self.transport) as client:
            for _ in range(max_pages):
                payload = await self._get_json(client, f"{self.base_url}/journals/{issn}/works", params)
                message = payload.get("message") or {}
                results.extend(self.normalize(item) for item in message.get("items", []))
                next_cursor = message.get("next-cursor")
                if not next_cursor or next_cursor == params["cursor"]:
                    break
                await self.wait_between_requests()
                params["cursor"] = next_cursor
        return results

    async def wait_between_requests(self) -> None:
        if self.request_interval_seconds > 0:
            await self.sleep(self.request_interval_seconds)

    async def _get_json(self, client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    await self.sleep(self.retry_delay(attempt, exc.response))
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    await self.sleep(self.retry_delay(attempt))
        raise RuntimeError(f"Crossref request failed: {last_error}")

    def retry_delay(self, attempt: int, response: Optional[httpx.Response] = None) -> float:
        if response is not None and response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(float(retry_after), 0.0)
                except ValueError:
                    pass
        return self.retry_backoff_seconds * (attempt + 1)

    def clean_abstract(self, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        without_tags = re.sub(r"<[^>]+>", " ", value)
        decoded = html.unescape(without_tags)
        return re.sub(r"\s+", " ", decoded).strip()

    def normalize(self, item: dict[str, Any]) -> dict[str, Any]:
        published = item.get("published-print") or item.get("published-online") or item.get("issued") or {}
        parts = (published.get("date-parts") or [[None]])[0]
        year = parts[0] if parts else None
        published_date = "-".join(str(p).zfill(2) for p in parts if p is not None) if parts else None
        authors = [
            {"name": " ".join(v for v in [a.get("given"), a.get("family")] if v), "affiliation": None}
            for a in item.get("author", [])
        ]
        return {
            "doi": item.get("DOI"),
            "title": (item.get("title") or ["Untitled"])[0],
            "abstract": self.clean_abstract(item.get("abstract")),
            "authors": authors,
            "journal_name": (item.get("container-title") or [None])[0],
            "published_date": published_date,
            "published_year": year,
            "landing_url": item.get("URL"),
            "source_api": "crossref",
            "raw_metadata": item,
        }
