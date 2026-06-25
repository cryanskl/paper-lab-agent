import asyncio
from datetime import date
from typing import Any, Optional

import httpx


class OpenAlexClient:
    base_url = "https://api.openalex.org"

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
        filters = [
            f"locations.source.issn:{issn}",
            f"from_publication_date:{date_from}",
            f"to_publication_date:{date_to}",
        ]
        params: dict[str, Any] = {"filter": ",".join(filters), "per-page": 100, "cursor": "*"}
        if self.mailto:
            params["mailto"] = self.mailto
        results: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            for _ in range(max_pages):
                payload = await self._get_json(client, f"{self.base_url}/works", params)
                if not isinstance(payload, dict):
                    break
                page_results = payload.get("results") or []
                if isinstance(page_results, list):
                    results.extend(self.normalize(item) for item in page_results if isinstance(item, dict))
                meta = payload.get("meta") or {}
                if not isinstance(meta, dict):
                    meta = {}
                next_cursor = meta.get("next_cursor")
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
        raise RuntimeError(f"OpenAlex request failed: {last_error}")

    def retry_delay(self, attempt: int, response: Optional[httpx.Response] = None) -> float:
        if response is not None and response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(float(retry_after), 0.0)
                except ValueError:
                    pass
        return self.retry_backoff_seconds * (attempt + 1)

    def abstract_text(self, item: dict[str, Any]) -> str:
        abstract = item.get("abstract")
        if isinstance(abstract, str) and abstract.strip():
            return abstract
        inverted = item.get("abstract_inverted_index")
        if not isinstance(inverted, dict):
            return ""
        positioned_words = []
        for word, positions in inverted.items():
            if not isinstance(positions, list):
                continue
            for position in positions:
                if isinstance(position, int) and position >= 0:
                    positioned_words.append((position, str(word)))
        positioned_words.sort(key=lambda pair: pair[0])
        return " ".join(word for _, word in positioned_words)

    def normalize_doi(self, value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        doi = value.strip().lower()
        if not doi:
            return None
        return doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/")

    def normalize_authors(self, value: Any) -> list[dict[str, Optional[str]]]:
        if not isinstance(value, list):
            return []
        authors = []
        for item in value:
            if not isinstance(item, dict):
                continue
            author = item.get("author") or {}
            if not isinstance(author, dict):
                continue
            name = author.get("display_name")
            if isinstance(name, str) and name:
                authors.append({"name": name, "affiliation": None})
        return authors

    def normalize_title(self, value: Any) -> str:
        if isinstance(value, str) and value.strip():
            return value
        return "Untitled"

    def normalize_publication_date(self, value: Any) -> Optional[str]:
        if isinstance(value, str) and value.strip():
            text = value.strip()
            try:
                date.fromisoformat(text)
            except ValueError:
                return None
            return text
        return None

    def normalize_publication_year(self, value: Any) -> Optional[int]:
        if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 9999:
            return value
        return None

    def normalize_optional_text(self, value: Any) -> Optional[str]:
        if isinstance(value, str) and value.strip():
            return value
        return None

    def normalize(self, item: dict[str, Any]) -> dict[str, Any]:
        doi = self.normalize_doi(item.get("doi"))
        primary_location = item.get("primary_location") or {}
        if not isinstance(primary_location, dict):
            primary_location = {}
        source = primary_location.get("source") or {}
        if not isinstance(source, dict):
            source = {}
        authors = self.normalize_authors(item.get("authorships"))
        abstract = self.abstract_text(item)
        return {
            "doi": doi,
            "title": self.normalize_title(item.get("title")),
            "abstract": abstract,
            "authors": authors,
            "journal_name": self.normalize_optional_text(source.get("display_name")),
            "published_date": self.normalize_publication_date(item.get("publication_date")),
            "published_year": self.normalize_publication_year(item.get("publication_year")),
            "landing_url": self.normalize_optional_text(primary_location.get("landing_page_url"))
            or self.normalize_optional_text(item.get("id")),
            "source_api": "openalex",
            "raw_metadata": item,
        }
