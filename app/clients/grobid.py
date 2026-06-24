from typing import Optional

import httpx


class GrobidClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def health(self) -> bool:
        detail = await self.health_detail()
        return bool(detail["available"])

    async def health_detail(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/isalive")
            available = response.status_code == 200 and response.text.strip().lower() in {"true", "alive"}
            return {
                "available": available,
                "url": self.base_url,
                "status_code": response.status_code,
                "error": None if available else f"unexpected health response: {response.text[:120]}",
            }
        except Exception as exc:
            return {"available": False, "url": self.base_url, "status_code": None, "error": str(exc)}

    async def process_fulltext(self, file_path: str) -> Optional[str]:
        async with httpx.AsyncClient(timeout=60) as client:
            with open(file_path, "rb") as handle:
                response = await client.post(
                    f"{self.base_url}/api/processFulltextDocument",
                    files={"input": (file_path, handle, "application/pdf")},
                )
            response.raise_for_status()
            return response.text
