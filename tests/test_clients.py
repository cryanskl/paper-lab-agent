import httpx
import pytest

from app.clients.crossref import CrossrefClient
from app.clients.openalex import OpenAlexClient
from app.clients.unpaywall import UnpaywallClient


def json_response(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload)


@pytest.mark.asyncio
async def test_openalex_waits_between_paginated_requests():
    sleep_calls = []
    seen_cursors = []

    async def sleep(delay: float) -> None:
        sleep_calls.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        cursor = request.url.params.get("cursor")
        seen_cursors.append(cursor)
        if cursor == "*":
            return json_response(
                {
                    "results": [{"id": "https://openalex.org/W1", "title": "First"}],
                    "meta": {"next_cursor": "next-page"},
                }
            )
        return json_response(
            {
                "results": [{"id": "https://openalex.org/W2", "title": "Second"}],
                "meta": {},
            }
        )

    client = OpenAlexClient(
        transport=httpx.MockTransport(handler),
        request_interval_seconds=0.75,
        sleep=sleep,
    )

    works = await client.works_by_issn("1234-5678", "2026-01-01", "2026-01-31", max_pages=2)

    assert [work["title"] for work in works] == ["First", "Second"]
    assert seen_cursors == ["*", "next-page"]
    assert sleep_calls == [0.75]


@pytest.mark.asyncio
async def test_crossref_waits_between_paginated_requests():
    sleep_calls = []
    seen_cursors = []

    async def sleep(delay: float) -> None:
        sleep_calls.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        cursor = request.url.params.get("cursor")
        seen_cursors.append(cursor)
        if cursor == "*":
            return json_response(
                {
                    "message": {
                        "items": [{"DOI": "10.1/first", "title": ["First"]}],
                        "next-cursor": "next-page",
                    }
                }
            )
        return json_response({"message": {"items": [{"DOI": "10.1/second", "title": ["Second"]}]}})

    client = CrossrefClient(
        transport=httpx.MockTransport(handler),
        request_interval_seconds=0.5,
        sleep=sleep,
    )

    works = await client.works_by_issn("1234-5678", "2026-01-01", "2026-01-31", max_pages=2)

    assert [work["title"] for work in works] == ["First", "Second"]
    assert seen_cursors == ["*", "next-page"]
    assert sleep_calls == [0.5]


@pytest.mark.asyncio
async def test_unpaywall_waits_after_successful_resolution():
    sleep_calls = []

    async def sleep(delay: float) -> None:
        sleep_calls.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "oa_status": "gold",
                "best_oa_location": {"url_for_pdf": "https://example.test/paper.pdf"},
            }
        )

    client = UnpaywallClient(
        email="dev@example.test",
        transport=httpx.MockTransport(handler),
        request_interval_seconds=0.25,
        sleep=sleep,
    )

    result = await client.resolve("10.1/example")

    assert result["oa_status"] == "gold"
    assert result["oa_pdf_url"] == "https://example.test/paper.pdf"
    assert sleep_calls == [0.25]
