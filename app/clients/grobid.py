from typing import Optional

import httpx


class GrobidClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/isalive")
            return response.status_code == 200 and response.text.strip().lower() in {"true", "alive"}
        except Exception:
            return False

    async def process_fulltext(self, file_path: str) -> Optional[str]:
        async with httpx.AsyncClient(timeout=60) as client:
            with open(file_path, "rb") as handle:
                response = await client.post(
                    f"{self.base_url}/api/processFulltextDocument",
                    files={"input": (file_path, handle, "application/pdf")},
                )
            response.raise_for_status()
            return response.text

