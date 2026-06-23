from typing import Any, Optional

import httpx


class UnpaywallClient:
    base_url = "https://api.unpaywall.org/v2"

    def __init__(self, email: Optional[str]):
        self.email = email

    async def resolve(self, doi: str) -> dict[str, Any]:
        if not self.email:
            return {"oa_status": "unknown", "oa_pdf_url": None, "error": "UNPAYWALL_EMAIL is not configured"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.base_url}/{doi}", params={"email": self.email})
            response.raise_for_status()
            payload = response.json()
        best = payload.get("best_oa_location") or {}
        return {
            "oa_status": payload.get("oa_status") or "unknown",
            "oa_pdf_url": best.get("url_for_pdf"),
            "raw": payload,
        }

