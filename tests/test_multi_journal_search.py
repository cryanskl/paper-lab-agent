import asyncio
import sqlite3

import httpx

from app.clients.crossref import CrossrefClient
from app.services import crawl as crawl_service


def candidate(doi: str, title: str, *, work_type: str = "article", abstract: str = "") -> dict:
    return {
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "authors": [],
        "published_date": "2026-01-01",
        "published_year": 2026,
        "source_api": "openalex",
        "work_type": work_type,
        "raw_metadata": {},
    }


def batch(job_id: int, journal_id: int, candidates: list[dict]) -> crawl_service.CrawlCandidateBatch:
    return crawl_service.CrawlCandidateBatch(
        job_id=job_id,
        journal_id=journal_id,
        journal={"id": journal_id, "name": f"Journal {journal_id}"},
        candidates=candidates,
        found=len(candidates),
    )


def test_balanced_selection_preserves_each_journals_provider_order():
    batches = [
        batch(10, 1, [candidate("10.1/a1", "A1"), candidate("10.1/a2", "A2"), candidate("10.1/a3", "A3")]),
        batch(11, 2, [candidate("10.2/b1", "B1"), candidate("10.2/b2", "B2"), candidate("10.2/b3", "B3")]),
        batch(12, 3, [candidate("10.3/c1", "C1"), candidate("10.3/c2", "C2"), candidate("10.3/c3", "C3")]),
    ]

    selected = crawl_service.select_balanced_candidates(batches, 5)

    assert [work["title"] for work in selected[10]] == ["A1", "A2"]
    assert [work["title"] for work in selected[11]] == ["B1", "B2"]
    assert [work["title"] for work in selected[12]] == ["C1"]
    assert sum(len(items) for items in selected.values()) == 5


def test_balanced_selection_redistributes_empty_slots_and_deduplicates_doi():
    batches = [
        batch(20, 1, []),
        batch(21, 2, [candidate("10.2/shared", "B1"), candidate("10.2/b2", "B2")]),
        batch(22, 3, [candidate("10.2/shared", "Duplicate"), candidate("10.3/c2", "C2")]),
    ]

    selected = crawl_service.select_balanced_candidates(batches, 3)

    assert selected[20] == []
    assert [work["title"] for work in selected[21]] == ["B1", "B2"]
    assert [work["title"] for work in selected[22]] == ["C2"]
    assert batches[2].filtered == 1


def test_non_research_metadata_records_are_rejected():
    assert crawl_service.is_research_work(candidate("10.1/article", "Article")) is True
    assert crawl_service.is_research_work(candidate("10.1/paratext", "Journal title", work_type="paratext")) is False
    assert crawl_service.is_research_work({"title": "Legacy record", "raw_metadata": {}}) is True


def test_missing_abstract_is_enriched_from_crossref_without_changing_primary_source():
    work = candidate("10.1/enriched", "Needs abstract")

    class FakeCrossref:
        async def work_by_doi(self, doi):
            assert doi == "10.1/enriched"
            return {
                "abstract": "Public Crossref abstract.",
                "authors": [{"name": "Ada Author", "affiliation": None}],
                "landing_url": "https://doi.org/10.1/enriched",
                "raw_metadata": {"DOI": doi},
            }

    enriched, error = asyncio.run(crawl_service.enrich_missing_abstract(work, FakeCrossref()))

    assert error is None
    assert enriched["abstract"] == "Public Crossref abstract."
    assert enriched["authors"][0]["name"] == "Ada Author"
    assert enriched["source_api"] == "openalex"
    assert enriched["raw_metadata"]["crossref_enrichment"]["DOI"] == "10.1/enriched"


def test_crossref_single_doi_lookup_encodes_path_and_normalizes_abstract():
    def handler(request):
        assert request.url.raw_path == b"/works/10.1%2Fenriched?mailto=lab%40example.test"
        return httpx.Response(
            200,
            json={
                "message": {
                    "DOI": "10.1/ENRICHED",
                    "title": ["Enriched paper"],
                    "abstract": "<jats:p>Public metadata abstract.</jats:p>",
                    "type": "journal-article",
                }
            },
        )

    client = CrossrefClient(
        mailto="lab@example.test",
        transport=httpx.MockTransport(handler),
    )
    work = asyncio.run(client.work_by_doi("10.1/enriched"))

    assert work["doi"] == "10.1/enriched"
    assert work["abstract"] == "Public metadata abstract."
    assert work["work_type"] == "journal-article"


def test_upsert_does_not_erase_existing_abstract_or_authors_with_empty_metadata():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE papers (
            id INTEGER PRIMARY KEY,
            doi TEXT UNIQUE,
            title TEXT,
            abstract TEXT,
            authors TEXT,
            journal_id INTEGER,
            journal_name TEXT,
            published_date TEXT,
            published_year INTEGER,
            landing_url TEXT,
            oa_status TEXT,
            oa_pdf_url TEXT,
            source_api TEXT,
            dedupe_key TEXT,
            raw_metadata TEXT,
            library_status TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO papers (doi, title, abstract, authors, raw_metadata, library_status)
        VALUES ('10.1/preserved', 'Old title', 'Existing abstract.', '[{"name":"Existing Author"}]', '{}', 'saved')
        """
    )
    work = candidate("10.1/preserved", "Updated title")

    created, paper_id = crawl_service.upsert_paper_record(
        conn,
        {"id": 7, "name": "Journal 7"},
        work,
        {"oa_status": "unknown", "oa_pdf_url": None},
    )
    row = conn.execute("SELECT * FROM papers WHERE id=?", (paper_id,)).fetchone()

    assert created is False
    assert row["title"] == "Updated title"
    assert row["abstract"] == "Existing abstract."
    assert row["authors"] == '[{"name":"Existing Author"}]'


def test_search_orchestrator_selects_only_after_all_journals_are_prepared(monkeypatch):
    events = []

    async def fake_prepare(job_id, journal_id, *_args):
        events.append(f"prepare-{job_id}")
        return batch(
            job_id,
            journal_id,
            [
                candidate(f"10.{journal_id}/1", f"J{journal_id}-1"),
                candidate(f"10.{journal_id}/2", f"J{journal_id}-2"),
            ],
        )

    async def fake_finalize(prepared, selected):
        assert len([event for event in events if isinstance(event, str) and event.startswith("prepare-")]) == 3
        events.append((prepared.job_id, [work["title"] for work in selected]))

    monkeypatch.setattr(crawl_service, "prepare_crawl_job", fake_prepare)
    monkeypatch.setattr(crawl_service, "finalize_crawl_batch", fake_finalize)
    task_args = [
        (31, 1, "2026-01-01", "2026-01-31", ["plasma"], "or", 4),
        (32, 2, "2026-01-01", "2026-01-31", ["plasma"], "or", 4),
        (33, 3, "2026-01-01", "2026-01-31", ["plasma"], "or", 4),
    ]

    asyncio.run(crawl_service.run_search_crawl_jobs(task_args, 4, max_concurrency=3))

    finalized = {event[0]: event[1] for event in events if isinstance(event, tuple)}
    assert finalized == {
        31: ["J1-1", "J1-2"],
        32: ["J2-1"],
        33: ["J3-1"],
    }
