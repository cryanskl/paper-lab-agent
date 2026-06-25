import asyncio
import html
import re
from datetime import date
from typing import Any, Optional
from urllib.parse import urlparse

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
        if self.mailto:
            params["mailto"] = self.mailto
        results: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers, transport=self.transport) as client:
            for _ in range(max_pages):
                payload = await self._get_json(client, f"{self.base_url}/journals/{issn}/works", params)
                if not isinstance(payload, dict):
                    break
                message = payload.get("message") or {}
                if not isinstance(message, dict):
                    message = {}
                items = message.get("items") or []
                if isinstance(items, list):
                    results.extend(self.normalize(item) for item in items if isinstance(item, dict))
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
                if not self.should_retry_response(exc.response):
                    break
                if attempt < self.max_retries - 1:
                    await self.sleep(self.retry_delay(attempt, exc.response))
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    await self.sleep(self.retry_delay(attempt))
        raise RuntimeError(f"Crossref request failed: {last_error}")

    def should_retry_response(self, response: httpx.Response) -> bool:
        return response.status_code == 429 or response.status_code >= 500

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

    def normalize_doi(self, value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        doi = value.strip().lower()
        if not doi:
            return None
        return (
            doi.removeprefix("https://doi.org/")
            .removeprefix("http://doi.org/")
            .removeprefix("https://dx.doi.org/")
            .removeprefix("http://dx.doi.org/")
            .removeprefix("doi:")
        )

    def first_text(self, value: Any, default: Optional[str] = None) -> Optional[str]:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    return item.strip()
        return default

    def normalize_authors(self, value: Any) -> list[dict[str, Optional[str]]]:
        if not isinstance(value, list):
            return []
        authors = []
        for item in value:
            if not isinstance(item, dict):
                continue
            name_parts = [
                value.strip()
                for value in [item.get("given"), item.get("family")]
                if isinstance(value, str) and value.strip()
            ]
            name = " ".join(name_parts)
            if name:
                authors.append({"name": name, "affiliation": None})
        return authors

    def normalize_url(self, value: Any) -> Optional[str]:
        if isinstance(value, str) and value.strip():
            text = value.strip()
            parsed = urlparse(text)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                return text
        return None

    def normalize_date_parts(self, value: Any) -> tuple[Optional[str], Optional[int]]:
        if not isinstance(value, list) or not value or not isinstance(value[0], list):
            return None, None
        parts = value[0]
        if not parts or len(parts) > 3 or any(isinstance(part, bool) or not isinstance(part, int) for part in parts):
            return None, None
        year = parts[0]
        month = parts[1] if len(parts) > 1 else 1
        day = parts[2] if len(parts) > 2 else 1
        try:
            parsed = date(year, month, day)
        except ValueError:
            return None, None
        return parsed.isoformat(), year

    def normalize(self, item: dict[str, Any]) -> dict[str, Any]:
        published = item.get("published-print") or item.get("published-online") or item.get("issued") or {}
        if not isinstance(published, dict):
            published = {}
        date_parts = published.get("date-parts")
        published_date, year = self.normalize_date_parts(date_parts)
        authors = self.normalize_authors(item.get("author"))
        return {
            "doi": self.normalize_doi(item.get("DOI")),
            "title": self.first_text(item.get("title"), "Untitled"),
            "abstract": self.clean_abstract(item.get("abstract")),
            "authors": authors,
            "journal_name": self.first_text(item.get("container-title")),
            "published_date": published_date,
            "published_year": year,
            "landing_url": self.normalize_url(item.get("URL")),
            "source_api": "crossref",
            "raw_metadata": item,
        }
