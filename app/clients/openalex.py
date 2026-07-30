import asyncio
import unicodedata
from datetime import date
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.clients.retry_after import retry_after_delay


class OpenAlexClient:
    base_url = "https://api.openalex.org"

    def __init__(
        self,
        mailto: Optional[str] = None,
        api_key: Optional[str] = None,
        transport: Optional[Any] = None,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.25,
        request_interval_seconds: float = 0.0,
        timeout: float = 20.0,
        sleep: Any = asyncio.sleep,
    ):
        self.mailto = mailto.strip() if isinstance(mailto, str) and mailto.strip() else None
        self.api_key = api_key.strip() if isinstance(api_key, str) and api_key.strip() else None
        self.transport = transport
        self.max_retries = max(1, max_retries)
        self.retry_backoff_seconds = retry_backoff_seconds
        self.request_interval_seconds = max(request_interval_seconds, 0.0)
        self.timeout = timeout
        self.sleep = sleep

    async def works_by_issn(self, issn: str, date_from: str, date_to: str, max_pages: int = 3) -> list[dict[str, Any]]:
        if not isinstance(issn, str):
            return []
        issn = unicodedata.normalize("NFKC", issn).strip()
        if not issn:
            return []
        max_pages = max(1, max_pages)
        filters = [
            f"locations.source.issn:{issn}",
            f"from_publication_date:{date_from}",
            f"to_publication_date:{date_to}",
        ]
        params: dict[str, Any] = {"filter": ",".join(filters), "per-page": 100, "cursor": "*"}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.mailto:
            params["mailto"] = self.mailto
        results: list[dict[str, Any]] = []
        headers = {}
        if self.mailto:
            headers["User-Agent"] = f"paper-lab-agent (mailto:{self.mailto})"
        async with httpx.AsyncClient(timeout=self.timeout, headers=headers, transport=self.transport) as client:
            for page_index in range(max_pages):
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
                if not isinstance(next_cursor, str) or not next_cursor or next_cursor == params["cursor"]:
                    break
                if page_index >= max_pages - 1:
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
        raise RuntimeError(f"OpenAlex request failed: {last_error}")

    def should_retry_response(self, response: httpx.Response) -> bool:
        return response.status_code == 429 or response.status_code >= 500

    def retry_delay(self, attempt: int, response: Optional[httpx.Response] = None) -> float:
        if response is not None and response.status_code == 429:
            parsed_delay = retry_after_delay(response)
            if parsed_delay is not None:
                return parsed_delay
        return self.retry_backoff_seconds * (attempt + 1)

    def abstract_text(self, item: dict[str, Any]) -> str:
        abstract = item.get("abstract")
        if isinstance(abstract, str) and abstract.strip():
            return " ".join(abstract.split())
        inverted = item.get("abstract_inverted_index")
        if not isinstance(inverted, dict):
            return ""
        positioned_words = []
        for word, positions in inverted.items():
            if not isinstance(positions, list):
                continue
            for position in positions:
                if isinstance(position, int) and not isinstance(position, bool) and position >= 0:
                    positioned_words.append((position, str(word)))
        positioned_words.sort(key=lambda pair: pair[0])
        return " ".join(word for _, word in positioned_words)

    def normalize_doi(self, value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        doi = unicodedata.normalize("NFKC", value).strip().lower()
        if not doi:
            return None
        return (
            doi.removeprefix("https://doi.org/")
            .removeprefix("http://doi.org/")
            .removeprefix("https://dx.doi.org/")
            .removeprefix("http://dx.doi.org/")
            .removeprefix("doi:")
        ).strip()

    def normalize_authors(self, value: Any) -> list[dict[str, Optional[str]]]:
        if not isinstance(value, list):
            return []
        authors = []
        for item in value:
            if not isinstance(item, dict):
                continue
            author = item.get("author") or {}
            if not isinstance(author, dict):
                author = {}
            name = self.author_name(item, author)
            if name:
                affiliation = self.normalize_affiliations(item.get("institutions")) or self.normalize_raw_affiliations(
                    item.get("raw_affiliation_strings")
                )
                authors.append({"name": name, "affiliation": affiliation})
        return authors

    def author_name(self, item: dict[str, Any], author: dict[str, Any]) -> Optional[str]:
        display_name = author.get("display_name")
        if isinstance(display_name, str) and display_name.strip():
            return display_name.strip()
        raw_author_name = item.get("raw_author_name")
        if isinstance(raw_author_name, str) and raw_author_name.strip():
            return raw_author_name.strip()
        return None

    def normalize_affiliations(self, value: Any) -> Optional[str]:
        if not isinstance(value, list):
            return None
        names = []
        for item in value:
            if not isinstance(item, dict):
                continue
            name = item.get("display_name")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
        return "; ".join(names) if names else None

    def normalize_raw_affiliations(self, value: Any) -> Optional[str]:
        if not isinstance(value, list):
            return None
        names = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        return "; ".join(names) if names else None

    def normalize_title(self, value: Any, fallback: Any = None) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(fallback, str) and fallback.strip():
            return fallback.strip()
        return "Untitled"

    def normalize_publication_date(self, value: Any, fallback_year: Optional[int] = None) -> Optional[str]:
        if isinstance(value, str) and value.strip():
            text = value.strip()
            try:
                date.fromisoformat(text)
            except ValueError:
                if fallback_year is not None:
                    return f"{fallback_year:04d}-01-01"
                return None
            return text
        if value is None and fallback_year is not None:
            return f"{fallback_year:04d}-01-01"
        return None

    def normalize_publication_year(self, value: Any) -> Optional[int]:
        if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 9999:
            return value
        return None

    def normalize_optional_text(self, value: Any) -> Optional[str]:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def normalize_url(self, value: Any) -> Optional[str]:
        text = self.normalize_optional_text(value)
        if not text:
            return None
        text = text.strip()
        parsed = urlparse(text)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        return text

    def first_location_landing_url(self, value: Any) -> Optional[str]:
        if not isinstance(value, list):
            return None
        for item in value:
            if not isinstance(item, dict):
                continue
            url = self.normalize_url(item.get("landing_page_url"))
            if url:
                return url
        return None

    def first_location_source_name(self, value: Any) -> Optional[str]:
        if not isinstance(value, list):
            return None
        for item in value:
            if not isinstance(item, dict):
                continue
            source = item.get("source") or {}
            if not isinstance(source, dict):
                continue
            name = self.normalize_optional_text(source.get("display_name"))
            if name:
                return name
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
        published_year = self.normalize_publication_year(item.get("publication_year"))
        return {
            "doi": doi,
            "title": self.normalize_title(item.get("title"), item.get("display_name")),
            "abstract": abstract,
            "authors": authors,
            "journal_name": self.normalize_optional_text(source.get("display_name"))
            or self.first_location_source_name(item.get("locations")),
            "published_date": self.normalize_publication_date(item.get("publication_date"), published_year),
            "published_year": published_year,
            "landing_url": self.normalize_url(primary_location.get("landing_page_url"))
            or self.first_location_landing_url(item.get("locations"))
            or self.normalize_url(item.get("id")),
            "source_api": "openalex",
            "raw_metadata": item,
        }
