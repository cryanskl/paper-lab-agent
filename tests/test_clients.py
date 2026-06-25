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


def test_crossref_normalizes_dx_doi_url_to_bare_identifier():
    client = CrossrefClient()

    work = client.normalize({"DOI": "https://dx.doi.org/10.5555/ABC.Def", "title": ["Example"]})

    assert work["doi"] == "10.5555/abc.def"


def test_crossref_normalizes_prefixed_doi_to_bare_identifier():
    client = CrossrefClient()

    work = client.normalize({"DOI": "doi:10.5555/ABC.Def", "title": ["Example"]})

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


def test_crossref_strips_text_fields():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/stripped-text",
            "title": ["  Trimmed title  "],
            "container-title": ["  Trimmed journal  "],
        }
    )

    assert work["title"] == "Trimmed title"
    assert work["journal_name"] == "Trimmed journal"


def test_crossref_skips_malformed_text_list_items():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/malformed-text-list",
            "title": [{"value": "Malformed"}, "Usable title"],
            "container-title": [{"value": "Malformed journal"}, "Usable journal"],
        }
    )
    untitled = client.normalize({"DOI": "10.5555/no-usable-title", "title": [{"value": "Malformed"}]})

    assert work["title"] == "Usable title"
    assert work["journal_name"] == "Usable journal"
    assert untitled["title"] == "Untitled"


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


def test_crossref_tolerates_malformed_author_name_parts():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/author-name-parts",
            "title": ["Author name parts"],
            "author": [
                {"given": {"value": "Jane"}, "family": "Doe"},
                {"given": "Solo", "family": ["Malformed"]},
            ],
        }
    )

    assert work["authors"] == [
        {"name": "Doe", "affiliation": None},
        {"name": "Solo", "affiliation": None},
    ]


def test_crossref_strips_author_name_parts():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/trimmed-authors",
            "title": ["Trimmed authors"],
            "author": [{"given": "  Jane  ", "family": "  Doe  "}],
        }
    )

    assert work["authors"] == [{"name": "Jane Doe", "affiliation": None}]


def test_crossref_preserves_author_affiliations():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/crossref-affiliations",
            "title": ["Crossref affiliations"],
            "author": [
                {
                    "given": "Jane",
                    "family": "Doe",
                    "affiliation": [
                        {"name": "Princeton Plasma Physics Laboratory"},
                        {"name": "  MIT Plasma Science  "},
                        {"name": {"value": "Malformed"}},
                        "malformed-affiliation",
                    ],
                }
            ],
        }
    )

    assert work["authors"] == [
        {
            "name": "Jane Doe",
            "affiliation": "Princeton Plasma Physics Laboratory; MIT Plasma Science",
        }
    ]


def test_crossref_tolerates_malformed_published_date_fields():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/malformed-date",
            "title": ["Malformed date"],
            "published-print": "not-a-date-object",
        }
    )

    assert work["doi"] == "10.5555/malformed-date"
    assert work["title"] == "Malformed date"
    assert work["published_date"] is None
    assert work["published_year"] is None


def test_crossref_rejects_non_integer_date_parts():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/string-date-parts",
            "title": ["String date parts"],
            "issued": {"date-parts": [["2026", "07", "15"]]},
        }
    )

    assert work["published_date"] is None
    assert work["published_year"] is None


def test_crossref_rejects_out_of_range_date_parts():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/out-of-range-date-parts",
            "title": ["Out of range date parts"],
            "issued": {"date-parts": [[2026, 13, 40]]},
        }
    )

    assert work["published_date"] is None
    assert work["published_year"] is None


def test_crossref_rejects_overlong_date_parts():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/overlong-date-parts",
            "title": ["Overlong date parts"],
            "issued": {"date-parts": [[2026, 7, 15, 9]]},
        }
    )

    assert work["published_date"] is None
    assert work["published_year"] is None


def test_crossref_expands_partial_date_parts_to_iso_dates():
    client = CrossrefClient()

    year_only = client.normalize(
        {
            "DOI": "10.5555/year-only",
            "title": ["Year only date parts"],
            "issued": {"date-parts": [[2026]]},
        }
    )
    year_month = client.normalize(
        {
            "DOI": "10.5555/year-month",
            "title": ["Year and month date parts"],
            "issued": {"date-parts": [[2026, 7]]},
        }
    )

    assert year_only["published_date"] == "2026-01-01"
    assert year_only["published_year"] == 2026
    assert year_month["published_date"] == "2026-07-01"
    assert year_month["published_year"] == 2026


def test_crossref_tolerates_malformed_landing_url_field():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/malformed-url",
            "title": ["Malformed URL"],
            "URL": {"value": "https://publisher.example/article"},
        }
    )

    assert work["landing_url"] is None


def test_crossref_rejects_unsafe_landing_url():
    client = CrossrefClient()

    unsafe_scheme = client.normalize(
        {
            "DOI": "10.5555/unsafe-url",
            "title": ["Unsafe landing URL"],
            "URL": "javascript:alert(1)",
        }
    )
    missing_host = client.normalize(
        {
            "DOI": "10.5555/missing-host-url",
            "title": ["Missing host landing URL"],
            "URL": "https:article",
        }
    )

    assert unsafe_scheme["landing_url"] is None
    assert missing_host["landing_url"] is None


def test_crossref_falls_back_to_resource_primary_url():
    client = CrossrefClient()

    work = client.normalize(
        {
            "DOI": "10.5555/resource-url",
            "title": ["Resource URL"],
            "URL": "javascript:alert(1)",
            "resource": {
                "primary": {
                    "URL": "  https://publisher.example/article  ",
                }
            },
        }
    )

    assert work["landing_url"] == "https://publisher.example/article"


def test_openalex_normalizes_url_doi_to_bare_identifier():
    client = OpenAlexClient()

    work = client.normalize({"doi": "https://doi.org/10.5555/ABC.Def", "title": "Example"})

    assert work["doi"] == "10.5555/abc.def"


def test_openalex_normalizes_dx_doi_url_to_bare_identifier():
    client = OpenAlexClient()

    work = client.normalize({"doi": "https://dx.doi.org/10.5555/ABC.Def", "title": "Example"})

    assert work["doi"] == "10.5555/abc.def"


def test_openalex_normalizes_prefixed_doi_to_bare_identifier():
    client = OpenAlexClient()

    work = client.normalize({"doi": "doi:10.5555/ABC.Def", "title": "Example"})

    assert work["doi"] == "10.5555/abc.def"


def test_openalex_tolerates_malformed_title_fields():
    client = OpenAlexClient()

    list_title = client.normalize({"id": "https://openalex.org/W-title-list", "title": ["List title"]})
    object_title = client.normalize({"id": "https://openalex.org/W-title-object", "title": {"value": "Object title"}})

    assert list_title["title"] == "Untitled"
    assert object_title["title"] == "Untitled"


def test_openalex_strips_text_fields():
    client = OpenAlexClient()

    work = client.normalize(
        {
            "id": "https://openalex.org/W-stripped-text",
            "title": "  Trimmed title  ",
            "abstract": "  Trimmed\n\tabstract   text  ",
            "primary_location": {"source": {"display_name": "  Trimmed journal  "}},
        }
    )

    assert work["title"] == "Trimmed title"
    assert work["abstract"] == "Trimmed abstract text"
    assert work["journal_name"] == "Trimmed journal"


def test_openalex_ignores_boolean_abstract_positions():
    client = OpenAlexClient()

    work = client.normalize(
        {
            "id": "https://openalex.org/W-boolean-abstract-positions",
            "title": "Boolean abstract positions",
            "abstract_inverted_index": {
                "bad": [True],
                "also_bad": [False],
                "valid": [0],
            },
        }
    )

    assert work["abstract"] == "valid"


def test_openalex_tolerates_malformed_publication_fields():
    client = OpenAlexClient()

    work = client.normalize(
        {
            "id": "https://openalex.org/W-publication-fields",
            "title": "Malformed publication fields",
            "publication_date": ["2026-01-01"],
            "publication_year": {"value": 2026},
        }
    )

    assert work["published_date"] is None
    assert work["published_year"] is None


def test_openalex_rejects_invalid_publication_date_string():
    client = OpenAlexClient()

    work = client.normalize(
        {
            "id": "https://openalex.org/W-invalid-date",
            "title": "Invalid publication date",
            "publication_date": "2026-13-40",
            "publication_year": 2026,
        }
    )

    assert work["published_date"] is None
    assert work["published_year"] == 2026


def test_openalex_rejects_out_of_range_publication_year():
    client = OpenAlexClient()

    zero_year = client.normalize(
        {
            "id": "https://openalex.org/W-zero-year",
            "title": "Zero publication year",
            "publication_year": 0,
        }
    )
    too_large_year = client.normalize(
        {
            "id": "https://openalex.org/W-too-large-year",
            "title": "Too large publication year",
            "publication_year": 10000,
        }
    )

    assert zero_year["published_year"] is None
    assert too_large_year["published_year"] is None


def test_openalex_tolerates_malformed_landing_url_fields():
    client = OpenAlexClient()

    malformed_primary_url = client.normalize(
        {
            "id": "https://openalex.org/W-safe-fallback",
            "title": "Malformed primary URL",
            "primary_location": {"landing_page_url": ["https://publisher.example/article"]},
        }
    )
    malformed_primary_and_id = client.normalize(
        {
            "id": {"value": "https://openalex.org/W-malformed-id"},
            "title": "Malformed primary URL and id",
            "primary_location": {"landing_page_url": {"value": "https://publisher.example/article"}},
        }
    )

    assert malformed_primary_url["landing_url"] == "https://openalex.org/W-safe-fallback"
    assert malformed_primary_and_id["landing_url"] is None


def test_openalex_rejects_unsafe_landing_url():
    client = OpenAlexClient()

    unsafe_primary_url = client.normalize(
        {
            "id": "https://openalex.org/W-unsafe-primary",
            "title": "Unsafe primary landing URL",
            "primary_location": {"landing_page_url": "javascript:alert(1)"},
        }
    )
    missing_host_id = client.normalize(
        {
            "id": "https:openalex-work",
            "title": "Missing host fallback URL",
            "primary_location": {"landing_page_url": ["malformed"]},
        }
    )

    assert unsafe_primary_url["landing_url"] == "https://openalex.org/W-unsafe-primary"
    assert missing_host_id["landing_url"] is None


def test_openalex_strips_landing_url_whitespace():
    client = OpenAlexClient()

    work = client.normalize(
        {
            "id": "https://openalex.org/W-whitespace-url",
            "title": "Whitespace landing URL",
            "primary_location": {"landing_page_url": "  https://publisher.example/article  "},
        }
    )

    assert work["landing_url"] == "https://publisher.example/article"


def test_openalex_falls_back_to_locations_landing_url():
    client = OpenAlexClient()

    work = client.normalize(
        {
            "id": "https://openalex.org/W-locations-url",
            "title": "Locations landing URL",
            "primary_location": {"landing_page_url": "javascript:alert(1)"},
            "locations": [
                "malformed-location",
                {"landing_page_url": "https:missing-host"},
                {"landing_page_url": "  https://publisher.example/article  "},
            ],
        }
    )

    assert work["landing_url"] == "https://publisher.example/article"


def test_openalex_tolerates_malformed_source_display_name():
    client = OpenAlexClient()

    work = client.normalize(
        {
            "id": "https://openalex.org/W-source-display-name",
            "title": "Malformed source display name",
            "primary_location": {"source": {"display_name": {"value": "Journal"}}},
        }
    )

    assert work["journal_name"] is None


def test_openalex_falls_back_to_locations_source_display_name():
    client = OpenAlexClient()

    work = client.normalize(
        {
            "id": "https://openalex.org/W-locations-source",
            "title": "Locations source",
            "primary_location": {"source": {"display_name": {"value": "Malformed"}}},
            "locations": [
                "malformed-location",
                {"source": "malformed-source"},
                {"source": {"display_name": "  Plasma Sources Science and Technology  "}},
            ],
        }
    )

    assert work["journal_name"] == "Plasma Sources Science and Technology"


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
                {"author": {"display_name": {"value": "Malformed"}}},
                {"author": {"display_name": ["Malformed"]}},
                {"author": {"display_name": "Solo"}},
            ],
        }
    )

    assert work["authors"] == [
        {"name": "Jane Doe", "affiliation": None},
        {"name": "Solo", "affiliation": None},
    ]


def test_openalex_strips_author_display_names():
    client = OpenAlexClient()

    work = client.normalize(
        {
            "doi": "10.5555/openalex-trimmed-authors",
            "title": "OpenAlex trimmed authors",
            "authorships": [{"author": {"display_name": "  Jane Doe  "}}],
        }
    )

    assert work["authors"] == [{"name": "Jane Doe", "affiliation": None}]


def test_openalex_preserves_author_institution_affiliations():
    client = OpenAlexClient()

    work = client.normalize(
        {
            "doi": "10.5555/openalex-affiliations",
            "title": "OpenAlex affiliations",
            "authorships": [
                {
                    "author": {"display_name": "Jane Doe"},
                    "institutions": [
                        {"display_name": "Princeton Plasma Physics Laboratory"},
                        {"display_name": "  MIT Plasma Science  "},
                        {"display_name": {"value": "Malformed"}},
                        "malformed-institution",
                    ],
                }
            ],
        }
    )

    assert work["authors"] == [
        {
            "name": "Jane Doe",
            "affiliation": "Princeton Plasma Physics Laboratory; MIT Plasma Science",
        }
    ]


def test_openalex_tolerates_malformed_primary_location_fields():
    client = OpenAlexClient()

    malformed_location = client.normalize(
        {
            "id": "https://openalex.org/W123",
            "doi": "10.5555/location",
            "title": "Malformed location",
            "primary_location": "not-a-location-object",
        }
    )
    malformed_source = client.normalize(
        {
            "id": "https://openalex.org/W124",
            "doi": "10.5555/source",
            "title": "Malformed source",
            "primary_location": {"source": "not-a-source-object"},
        }
    )

    assert malformed_location["landing_url"] == "https://openalex.org/W123"
    assert malformed_location["journal_name"] is None
    assert malformed_source["landing_url"] == "https://openalex.org/W124"
    assert malformed_source["journal_name"] is None


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
async def test_openalex_skips_malformed_result_items():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "results": [
                    "malformed-work",
                    {"id": "https://openalex.org/W1", "title": "Valid work"},
                ],
                "meta": {},
            }
        )

    client = OpenAlexClient(transport=httpx.MockTransport(handler))

    works = await client.works_by_issn("1234-5678", "2026-01-01", "2026-01-31", max_pages=1)

    assert [work["title"] for work in works] == ["Valid work"]


@pytest.mark.asyncio
async def test_openalex_tolerates_malformed_meta_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "results": [{"id": "https://openalex.org/W1", "title": "Valid work"}],
                "meta": "not-a-meta-object",
            }
        )

    client = OpenAlexClient(transport=httpx.MockTransport(handler))

    works = await client.works_by_issn("1234-5678", "2026-01-01", "2026-01-31", max_pages=1)

    assert [work["title"] for work in works] == ["Valid work"]


@pytest.mark.asyncio
async def test_openalex_tolerates_malformed_top_level_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(["not-a-response-object"])

    client = OpenAlexClient(transport=httpx.MockTransport(handler))

    works = await client.works_by_issn("1234-5678", "2026-01-01", "2026-01-31", max_pages=1)

    assert works == []


@pytest.mark.asyncio
async def test_openalex_does_not_retry_permanent_http_errors():
    calls = 0
    sleep_calls = []

    async def sleep(delay: float) -> None:
        sleep_calls.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "bad filter"}, request=request)

    client = OpenAlexClient(
        transport=httpx.MockTransport(handler),
        max_retries=3,
        sleep=sleep,
    )

    with pytest.raises(RuntimeError, match="OpenAlex request failed"):
        await client.works_by_issn("bad issn", "2026-01-01", "2026-01-31", max_pages=1)

    assert calls == 1
    assert sleep_calls == []


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
async def test_crossref_skips_malformed_result_items():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "message": {
                    "items": [
                        "malformed-work",
                        {"DOI": "10.1/valid", "title": ["Valid work"]},
                    ]
                }
            }
        )

    client = CrossrefClient(transport=httpx.MockTransport(handler))

    works = await client.works_by_issn("1234-5678", "2026-01-01", "2026-01-31", max_pages=1)

    assert [work["title"] for work in works] == ["Valid work"]


@pytest.mark.asyncio
async def test_crossref_tolerates_malformed_message_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response({"message": "not-a-message-object"})

    client = CrossrefClient(transport=httpx.MockTransport(handler))

    works = await client.works_by_issn("1234-5678", "2026-01-01", "2026-01-31", max_pages=1)

    assert works == []


@pytest.mark.asyncio
async def test_crossref_tolerates_malformed_top_level_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(["not-a-response-object"])

    client = CrossrefClient(transport=httpx.MockTransport(handler))

    works = await client.works_by_issn("1234-5678", "2026-01-01", "2026-01-31", max_pages=1)

    assert works == []


@pytest.mark.asyncio
async def test_crossref_does_not_retry_permanent_http_errors():
    calls = 0
    sleep_calls = []

    async def sleep(delay: float) -> None:
        sleep_calls.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404, json={"message": "unknown journal"}, request=request)

    client = CrossrefClient(
        transport=httpx.MockTransport(handler),
        max_retries=3,
        sleep=sleep,
    )

    with pytest.raises(RuntimeError, match="Crossref request failed"):
        await client.works_by_issn("0000-0000", "2026-01-01", "2026-01-31", max_pages=1)

    assert calls == 1
    assert sleep_calls == []


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


@pytest.mark.asyncio
async def test_unpaywall_does_not_retry_permanent_http_errors():
    calls = 0
    sleep_calls = []

    async def sleep(delay: float) -> None:
        sleep_calls.append(delay)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404, json={"error": "unknown doi"}, request=request)

    client = UnpaywallClient(
        email="dev@example.test",
        transport=httpx.MockTransport(handler),
        max_retries=3,
        sleep=sleep,
    )

    with pytest.raises(RuntimeError, match="Unpaywall request failed"):
        await client.resolve("10.1/missing")

    assert calls == 1
    assert sleep_calls == []


@pytest.mark.asyncio
async def test_unpaywall_tolerates_malformed_best_oa_location():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "oa_status": "green",
                "best_oa_location": "not-a-location-object",
            }
        )

    client = UnpaywallClient(
        email="dev@example.test",
        transport=httpx.MockTransport(handler),
    )

    result = await client.resolve("10.1/malformed-location")

    assert result["oa_status"] == "green"
    assert result["oa_pdf_url"] is None


@pytest.mark.asyncio
async def test_unpaywall_rejects_non_web_pdf_url_scheme():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "oa_status": "green",
                "best_oa_location": {"url_for_pdf": "javascript:alert(1)"},
            }
        )

    client = UnpaywallClient(
        email="dev@example.test",
        transport=httpx.MockTransport(handler),
    )

    result = await client.resolve("10.1/non-web-url")

    assert result["oa_status"] == "green"
    assert result["oa_pdf_url"] is None


@pytest.mark.asyncio
async def test_unpaywall_falls_back_to_pdf_url_when_url_for_pdf_is_invalid():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "oa_status": "green",
                "best_oa_location": {
                    "url_for_pdf": "javascript:alert(1)",
                    "url": "https://repository.example/paper.pdf",
                },
            }
        )

    client = UnpaywallClient(
        email="dev@example.test",
        transport=httpx.MockTransport(handler),
    )

    result = await client.resolve("10.1/pdf-url-fallback")

    assert result["oa_status"] == "green"
    assert result["oa_pdf_url"] == "https://repository.example/paper.pdf"


@pytest.mark.asyncio
async def test_unpaywall_rejects_web_pdf_url_without_host():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "oa_status": "green",
                "best_oa_location": {"url_for_pdf": "https:paper.pdf"},
            }
        )

    client = UnpaywallClient(
        email="dev@example.test",
        transport=httpx.MockTransport(handler),
    )

    result = await client.resolve("10.1/no-host-url")

    assert result["oa_status"] == "green"
    assert result["oa_pdf_url"] is None


@pytest.mark.asyncio
async def test_unpaywall_tolerates_malformed_top_level_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(["not-a-response-object"])

    client = UnpaywallClient(
        email="dev@example.test",
        transport=httpx.MockTransport(handler),
    )

    result = await client.resolve("10.1/malformed-payload")

    assert result["oa_status"] == "unknown"
    assert result["oa_pdf_url"] is None
    assert result["error"] == "Unpaywall response was not a JSON object"
