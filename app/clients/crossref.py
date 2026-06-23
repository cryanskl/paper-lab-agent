from typing import Any, Optional

import httpx


class CrossrefClient:
    base_url = "https://api.crossref.org"

    def __init__(self, mailto: Optional[str] = None):
        self.mailto = mailto

    async def works_by_issn(self, issn: str, date_from: str, date_to: str) -> list[dict[str, Any]]:
        headers = {}
        if self.mailto:
            headers["User-Agent"] = f"paper-lab-agent (mailto:{self.mailto})"
        params = {
            "filter": f"from-pub-date:{date_from},until-pub-date:{date_to}",
            "rows": 50,
        }
        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            response = await client.get(f"{self.base_url}/journals/{issn}/works", params=params)
            response.raise_for_status()
            payload = response.json()
        items = (payload.get("message") or {}).get("items", [])
        return [self.normalize(item) for item in items]

    def normalize(self, item: dict[str, Any]) -> dict[str, Any]:
        published = item.get("published-print") or item.get("published-online") or {}
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
            "abstract": item.get("abstract") or "",
            "authors": authors,
            "journal_name": (item.get("container-title") or [None])[0],
            "published_date": published_date,
            "published_year": year,
            "landing_url": item.get("URL"),
            "source_api": "crossref",
            "raw_metadata": item,
        }

