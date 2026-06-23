from typing import Any, Optional

import httpx


class OpenAlexClient:
    base_url = "https://api.openalex.org"

    def __init__(self, mailto: Optional[str] = None):
        self.mailto = mailto

    async def works_by_issn(self, issn: str, date_from: str, date_to: str) -> list[dict[str, Any]]:
        filters = [
            f"locations.source.issn:{issn}",
            f"from_publication_date:{date_from}",
            f"to_publication_date:{date_to}",
        ]
        params: dict[str, Any] = {"filter": ",".join(filters), "per-page": 50}
        if self.mailto:
            params["mailto"] = self.mailto
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.base_url}/works", params=params)
            response.raise_for_status()
            payload = response.json()
        return [self.normalize(item) for item in payload.get("results", [])]

    def normalize(self, item: dict[str, Any]) -> dict[str, Any]:
        doi = item.get("doi")
        if isinstance(doi, str) and doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")
        primary_location = item.get("primary_location") or {}
        source = primary_location.get("source") or {}
        authorships = item.get("authorships") or []
        authors = [
            {"name": (a.get("author") or {}).get("display_name"), "affiliation": None}
            for a in authorships
            if (a.get("author") or {}).get("display_name")
        ]
        abstract = item.get("abstract")
        return {
            "doi": doi,
            "title": item.get("title") or "Untitled",
            "abstract": abstract or "",
            "authors": authors,
            "journal_name": source.get("display_name"),
            "published_date": item.get("publication_date"),
            "published_year": item.get("publication_year"),
            "landing_url": item.get("id") or primary_location.get("landing_page_url"),
            "source_api": "openalex",
            "raw_metadata": item,
        }

