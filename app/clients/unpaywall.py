import asyncio
from typing import Any, Optional

import httpx


class UnpaywallClient:
    base_url = "https://api.unpaywall.org/v2"

    def __init__(self, email: Optional[str], transport: Optional[Any] = None):
        self.email = email
        self.transport = transport

    async def resolve(self, doi: str) -> dict[str, Any]:
        if not self.email:
            return {"oa_status": "unknown", "oa_pdf_url": None, "error": "UNPAYWALL_EMAIL is not configured"}
        async with httpx.AsyncClient(timeout=20, transport=self.transport) as client:
            payload = await self._get_json(client, f"{self.base_url}/{doi}", {"email": self.email})
        best = payload.get("best_oa_location") or {}
        return {
            "oa_status": payload.get("oa_status") or "unknown",
            "oa_pdf_url": best.get("url_for_pdf"),
            "raw": payload,
        }

    async def _get_json(self, client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < 2:
                    await asyncio.sleep(0.25 * (attempt + 1))
        raise RuntimeError(f"Unpaywall request failed: {last_error}")
