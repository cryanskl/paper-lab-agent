import httpx
import pytest

from app.clients.crossref import CrossrefClient
from app.clients.openalex import OpenAlexClient
from app.clients.unpaywall import UnpaywallClient


def json_response(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload)


def test_crossref_normalizes_url_doi_to_bare_identifier():
    client = CrossrefClient()

    work = client.normalize({"DOI": "https://doi.org/10.5555/ABC.Def", "title": ["Example"]})

    assert work["doi"] == "10.5555/abc.def"


def test_crossref_normalizes_scalar_title_fields():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/scalar-title",
            "title": "Scalar title",
            "container-title": "Scalar journal",
        }
    )

    assert work["title"] == "Scalar title"
    assert work["journal_name"] == "Scalar journal"


def test_crossref_skips_malformed_author_items():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/authors",
            "title": ["Author robustness"],
            "author": [
                {"given": "Jane", "family": "Doe"},
                "malformed-author",
                {"family": "Solo"},
            ],
        }
    )

    assert work["authors"] == [
        {"name": "Jane Doe", "affiliation": None},
        {"name": "Solo", "affiliation": None},
    ]


def test_openalex_normalizes_url_doi_to_bare_identifier():
    client = OpenAlexClient()

    work = client.normalize({"doi": "https://doi.org/10.5555/ABC.Def", "title": "Example"})

    assert work["doi"] == "10.5555/abc.def"


def test_openalex_skips_malformed_authorship_items():
    client = OpenAlexClient()

    work = client.normalize(
        {
            "doi": "10.5555/openalex-authors",
            "title": "OpenAlex author robustness",
            "authorships": [
                {"author": {"display_name": "Jane Doe"}},
                "malformed-authorship",
                {"author": "malformed-author"},
                {"author": {"display_name": "Solo"}},
            ],
        }
    )

    assert work["authors"] == [
        {"name": "Jane Doe", "affiliation": None},
        {"name": "Solo", "affiliation": None},
    ]


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
async def test_crossref_includes_mailto_in_request_params_and_user_agent():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["mailto"] = request.url.params.get("mailto")
        captured["user_agent"] = request.headers.get("User-Agent")
        return json_response({"message": {"items": []}})

    client = CrossrefClient(
        mailto="lab@example.test",
        transport=httpx.MockTransport(handler),
    )

    works = await client.works_by_issn("1234-5678", "2026-01-01", "2026-01-31", max_pages=1)

    assert works == []
    assert captured["mailto"] == "lab@example.test"
    assert captured["user_agent"] == "paper-lab-agent (mailto:lab@example.test)"


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
