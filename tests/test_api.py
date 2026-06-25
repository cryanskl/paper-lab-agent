import os
from pathlib import Path


def pdf_bytes(content: bytes) -> bytes:
    return b"%PDF-1.4\n" + content


def health_check_counts(**overrides):
    counts = {
        "journals": 6,
        "papers": 1,
        "categories": 7,
        "paper_categories": 0,
        "crawl_jobs": 0,
        "documents": 0,
        "sections": 0,
        "translations": 0,
        "chunks": 0,
        "reaction_sets": 0,
        "reactions": 0,
        "reaction_audits": 0,
    }
    counts.update(overrides)
    return counts


def health_check_status_counts(**overrides):
    status_counts = {
        "crawl_jobs": {},
        "document_parse": {},
        "document_index": {},
        "document_chemistry": {},
        "translations": {},
        "reaction_sets": {},
    }
    status_counts.update(overrides)
    return status_counts


def health_check_runtime(**overrides):
    runtime = {
        "api_prefix": "/api/v1",
        "scheduler_enabled": False,
        "scheduler_jobs": [
            {"id": "crawl-daily", "period": "daily", "trigger": "cron", "schedule": "day=*, hour=2", "timezone": "UTC"},
            {
                "id": "crawl-weekly",
                "period": "weekly",
                "trigger": "cron",
                "schedule": "day_of_week=mon, hour=3",
                "timezone": "UTC",
            },
            {
                "id": "crawl-monthly",
                "period": "monthly",
                "trigger": "cron",
                "schedule": "day=1, hour=4",
                "timezone": "UTC",
            },
        ],
        "version": "0.1.0",
    }
    runtime.update(overrides)
    return runtime


def health_check_storage_health(**overrides):
    storage_health = {
        "data_dir": {"path": "/tmp/data", "exists": True, "writable": True},
        "pdf_dir": {"path": "/tmp/data/pdfs", "exists": True, "writable": True},
        "tei_dir": {"path": "/tmp/data/tei", "exists": True, "writable": True},
        "translation_dir": {"path": "/tmp/data/translations", "exists": True, "writable": True},
        "export_dir": {"path": "/tmp/data/exports", "exists": True, "writable": True},
        "database": {"path": "/tmp/plasma.db", "exists": True, "writable": True},
        "database_parent": {"path": "/tmp", "exists": True, "writable": True},
        "vector_db_parent": {"path": "/tmp/data", "exists": True, "writable": True},
        "vector_db": {
            "path": "/tmp/data/vector-index.json",
            "exists": False,
            "readable": False,
            "writable": False,
            "valid_json": None,
            "error": None,
        },
    }
    storage_health.update(overrides)
    return storage_health


def make_client(tmp_path):
    os.environ["DATABASE_PATH"] = str(tmp_path / "test.db")
    os.environ["PAPER_LAB_DATA_DIR"] = str(tmp_path)
    os.environ["PAPER_LAB_PDF_DIR"] = str(tmp_path / "pdfs")
    os.environ["PAPER_LAB_TEI_DIR"] = str(tmp_path / "tei")
    os.environ["PAPER_LAB_TRANSLATION_DIR"] = str(tmp_path / "translations")
    os.environ["PAPER_LAB_EXPORT_DIR"] = str(tmp_path / "exports")
    os.environ["VECTOR_DB_PATH"] = str(tmp_path / "vector-index.json")

    from app.config import get_settings
    from app.db import init_db
    from app.main import app
    from fastapi.testclient import TestClient

    get_settings.cache_clear()
    init_db()
    return TestClient(app)


def test_health_seed_and_search(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/v1/journals?active=true").json()["total"] == 6
    assert len(client.get("/api/v1/categories").json()["items"]) == 7
    system = client.get("/api/v1/system/status").json()
    assert system["counts"]["journals"] == 6
    assert system["counts"]["categories"] == 7
    assert system["counts"]["crawl_jobs"] == 0
    assert system["counts"]["reaction_sets"] == 0
    assert system["counts"]["reactions"] == 0
    assert system["runtime"]["scheduler_enabled"] is False
    assert system["runtime"]["version"] == "0.1.0"
    storage_health = system["storage_health"]
    for required in [
        "data_dir",
        "pdf_dir",
        "tei_dir",
        "translation_dir",
        "export_dir",
        "database",
        "database_parent",
        "vector_db_parent",
    ]:
        assert storage_health[required]["exists"] is True
        assert isinstance(storage_health[required]["writable"], bool)
    assert storage_health["database"]["path"] == system["database_path"]

    from app.db import get_conn

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (
                doi, title, abstract, authors, journal_id, journal_name,
                published_date, published_year, landing_url, oa_status,
                oa_pdf_url, source_api, raw_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "10.1/test",
                "Global model of Ar/O2 inductively coupled plasma",
                "plasma chemistry simulation",
                "[]",
                2,
                "Plasma Sources Science and Technology",
                "2026-01-01",
                2026,
                "https://example.test",
                "green",
                "https://example.test/a.pdf",
                "fixture",
                "{}",
            ),
        )

    papers = client.get("/api/v1/papers?q=plasma").json()
    assert papers["total"] == 1
    paper_id = papers["items"][0]["id"]
    classified = client.post(f"/api/v1/papers/{paper_id}/classify").json()
    assert "chemistry" in classified["categories"]
    overridden = client.put(
        f"/api/v1/papers/{paper_id}/categories",
        json={"category_ids": [2, 6], "method": "manual"},
    ).json()
    assert set(overridden["categories"]) == {"chemistry", "methods"}
    assert overridden["category_details"] == [
        {
            "id": 2,
            "slug": "chemistry",
            "name": "等离子体化学",
            "confidence": 1.0,
            "method": "manual",
        },
        {
            "id": 6,
            "slug": "methods",
            "name": "仿真方法",
            "confidence": 1.0,
            "method": "manual",
        },
    ]


def test_paper_category_override_deduplicates_category_ids(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, '[]', 'fixture', '{}')
            """,
            ("Duplicate category override", "argon plasma",),
        )
        paper_id = conn.execute("SELECT id FROM papers WHERE title=?", ("Duplicate category override",)).fetchone()["id"]

    response = client.put(
        f"/api/v1/papers/{paper_id}/categories",
        json={"category_ids": [2, 2, 6], "method": "manual"},
    )

    assert response.status_code == 200
    assert response.json()["categories"].count("chemistry") == 1
    assert response.json()["categories"].count("methods") == 1


def test_paper_category_override_rejects_blank_method(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, '[]', 'fixture', '{}')
            """,
            ("Blank method category override", "argon plasma",),
        )
        paper_id = conn.execute("SELECT id FROM papers WHERE title=?", ("Blank method category override",)).fetchone()[
            "id"
        ]

    response = client.put(
        f"/api/v1/papers/{paper_id}/categories",
        json={"category_ids": [2], "method": "   "},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_paper_category_override_rejects_non_manual_method(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, '[]', 'fixture', '{}')
            """,
            ("Non-manual method category override", "argon plasma",),
        )
        paper_id = conn.execute(
            "SELECT id FROM papers WHERE title=?", ("Non-manual method category override",)
        ).fetchone()["id"]

    response = client.put(
        f"/api/v1/papers/{paper_id}/categories",
        json={"category_ids": [2], "method": "auto"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM paper_categories WHERE paper_id=?", (paper_id,)).fetchall()
    assert rows == []


def test_classify_paper_records_classifier_confidence(tmp_path, monkeypatch):
    client = make_client(tmp_path)

    from app.db import get_conn
    from app.routers import papers as papers_router

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, '[]', 'fixture', '{}')
            """,
            ("Classifier confidence paper", "no taxonomy keyword here",),
        )
        paper_id = conn.execute("SELECT id FROM papers WHERE title=?", ("Classifier confidence paper",)).fetchone()[
            "id"
        ]

    class FakeClassifier:
        def classify(self, text, categories):
            assert "Classifier confidence paper" in text
            assert any(category["slug"] == "chemistry" for category in categories)
            return [{"category_id": 2, "slug": "chemistry", "confidence": 0.91, "method": "auto"}]

    monkeypatch.setattr(papers_router, "get_classifier", lambda settings: FakeClassifier(), raising=False)

    response = client.post(f"/api/v1/papers/{paper_id}/classify")

    assert response.status_code == 200
    assert response.json()["categories"] == ["chemistry"]
    assert response.json()["category_details"] == [
        {
            "id": 2,
            "slug": "chemistry",
            "name": "等离子体化学",
            "confidence": 0.91,
            "method": "auto",
        }
    ]
    with get_conn() as conn:
        row = conn.execute(
            "SELECT confidence, method FROM paper_categories WHERE paper_id=? AND category_id=2",
            (paper_id,),
        ).fetchone()
    assert row["confidence"] == 0.91
    assert row["method"] == "auto"


def test_classify_paper_ignores_classifier_categories_outside_taxonomy(tmp_path, monkeypatch):
    client = make_client(tmp_path)

    from app.db import get_conn
    from app.routers import papers as papers_router

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, '[]', 'fixture', '{}')
            """,
            ("Classifier taxonomy guard paper", "plasma chemistry",),
        )
        paper_id = conn.execute(
            "SELECT id FROM papers WHERE title=?", ("Classifier taxonomy guard paper",)
        ).fetchone()["id"]

    class OutOfTaxonomyClassifier:
        def classify(self, text, categories):
            return [
                {"category_id": 2, "slug": "chemistry", "confidence": 0.91, "method": "auto"},
                {"category_id": 9999, "slug": "imagined-category", "confidence": 0.99, "method": "auto"},
            ]

    monkeypatch.setattr(papers_router, "get_classifier", lambda settings: OutOfTaxonomyClassifier(), raising=False)

    response = client.post(f"/api/v1/papers/{paper_id}/classify")

    assert response.status_code == 200
    assert response.json()["categories"] == ["chemistry"]
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT category_id, confidence, method FROM paper_categories WHERE paper_id=?",
            (paper_id,),
        ).fetchall()
    assert [(row["category_id"], row["confidence"], row["method"]) for row in rows] == [(2, 0.91, "auto")]


def test_local_classifier_does_not_invent_default_category(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, '[]', 'fixture', '{}')
            """,
            ("Out of scope material paper", "thermal coating measurements without taxonomy terms",),
        )
        paper_id = conn.execute("SELECT id FROM papers WHERE title=?", ("Out of scope material paper",)).fetchone()[
            "id"
        ]

    response = client.post(f"/api/v1/papers/{paper_id}/classify")

    assert response.status_code == 200
    assert response.json()["categories"] == []
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM paper_categories WHERE paper_id=?", (paper_id,)).fetchall()
    assert rows == []


def test_classify_paper_preserves_manual_category_overrides(tmp_path, monkeypatch):
    client = make_client(tmp_path)

    from app.db import get_conn
    from app.routers import papers as papers_router

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, '[]', 'fixture', '{}')
            """,
            ("Manual priority paper", "plasma chemistry methods",),
        )
        paper_id = conn.execute("SELECT id FROM papers WHERE title=?", ("Manual priority paper",)).fetchone()["id"]
        conn.execute(
            """
            INSERT INTO paper_categories (paper_id, category_id, confidence, method)
            VALUES (?, ?, ?, ?)
            """,
            (paper_id, 2, 1.0, "manual"),
        )

    class FakeClassifier:
        def classify(self, text, categories):
            return [
                {"category_id": 2, "slug": "chemistry", "confidence": 0.42, "method": "auto"},
                {"category_id": 6, "slug": "methods", "confidence": 0.88, "method": "auto"},
            ]

    monkeypatch.setattr(papers_router, "get_classifier", lambda settings: FakeClassifier(), raising=False)

    response = client.post(f"/api/v1/papers/{paper_id}/classify")

    assert response.status_code == 200
    assert set(response.json()["categories"]) == {"chemistry", "methods"}
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT category_id, confidence, method FROM paper_categories WHERE paper_id=? ORDER BY category_id",
            (paper_id,),
        ).fetchall()
    assert [(row["category_id"], row["confidence"], row["method"]) for row in rows] == [
        (2, 1.0, "manual"),
        (6, 0.88, "auto"),
    ]


def test_classify_paper_failure_returns_json_error(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.db import get_conn
    from app.main import app
    from app.routers import papers as papers_router
    from fastapi.testclient import TestClient

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, '[]', 'fixture', '{}')
            """,
            ("Classifier outage paper", "plasma chemistry",),
        )
        paper_id = conn.execute("SELECT id FROM papers WHERE title=?", ("Classifier outage paper",)).fetchone()["id"]

    class FailingClassifier:
        def classify(self, text, categories):
            raise RuntimeError("classifier backend unavailable")

    monkeypatch.setattr(papers_router, "get_classifier", lambda settings: FailingClassifier(), raising=False)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(f"/api/v1/papers/{paper_id}/classify")

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "paper_classification_failed"
    assert "classifier backend unavailable" in payload["error"]["message"]


def test_papers_reject_unknown_sort(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/v1/papers", params={"sort": "title_asc"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_papers_reject_relevance_sort_without_query(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/v1/papers", params={"sort": "relevance"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "sort=relevance requires q" in response.json()["error"]["message"]


def test_papers_reject_reversed_year_range(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/v1/papers", params={"year_from": 2026, "year_to": 2025})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_papers_treat_blank_query_as_unfiltered_list(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, '[]', 'fixture', '{}')
            """,
            ("Blank query should not hit FTS", "argon plasma",),
        )

    response = client.get("/api/v1/papers", params={"q": "   "})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Blank query should not hit FTS"


def test_papers_search_handles_special_characters(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, '[]', 'fixture', '{}')
            """,
            ("Ar/O2 plasma chemistry model", "global discharge model",),
        )

    response = client.get("/api/v1/papers", params={"q": "Ar/O2"})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Ar/O2 plasma chemistry model"


def test_papers_treat_blank_category_as_unfiltered_list(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, '[]', 'fixture', '{}')
            """,
            ("Blank category should not filter results", "argon plasma",),
        )

    response = client.get("/api/v1/papers", params={"category": "   "})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Blank category should not filter results"


def test_crawl_job_detail_includes_journal_and_diagnostics(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO crawl_jobs (
                journal_id, period, date_from, date_to, status,
                papers_found, papers_filtered, papers_new, error,
                started_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                2,
                "manual",
                "2026-06-01",
                "2026-06-23",
                "failed",
                12,
                5,
                3,
                "OpenAlex timeout",
                "2026-06-23T10:00:00",
                "2026-06-23T10:01:00",
            ),
        )
        job_id = cursor.lastrowid

    response = client.get(f"/api/v1/crawl/jobs/{job_id}")

    assert response.status_code == 200
    detail = response.json()
    assert detail["journal"]["id"] == 2
    assert detail["journal"]["name"] == "Plasma Sources Science and Technology"
    assert detail["diagnostics"] == {
        "journal_id": 2,
        "journal_name": "Plasma Sources Science and Technology",
        "period": "manual",
        "date_from": "2026-06-01",
        "date_to": "2026-06-23",
        "status": "failed",
        "papers_found": 12,
        "papers_filtered": 5,
        "papers_new": 3,
        "papers_accepted": 7,
        "papers_existing": 4,
        "error": "OpenAlex timeout",
    }


def test_crawl_job_list_includes_journal_and_diagnostics(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO crawl_jobs (
                journal_id, period, date_from, date_to, status,
                papers_found, papers_filtered, papers_new, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (3, "weekly", "2026-06-01", "2026-06-07", "success", 8, 2, 4, "Crossref fallback"),
        )

    response = client.get("/api/v1/crawl/jobs")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["journal"]["id"] == 3
    assert item["journal"]["name"] == "Plasma Chemistry and Plasma Processing"
    assert item["diagnostics"] == {
        "journal_id": 3,
        "journal_name": "Plasma Chemistry and Plasma Processing",
        "period": "weekly",
        "date_from": "2026-06-01",
        "date_to": "2026-06-07",
        "status": "success",
        "papers_found": 8,
        "papers_filtered": 2,
        "papers_new": 4,
        "papers_accepted": 6,
        "papers_existing": 2,
        "error": "Crossref fallback",
    }


def test_journal_crud_accepts_keyword_config_and_soft_deletes(tmp_path):
    client = make_client(tmp_path)

    created = client.post(
        "/api/v1/journals",
        json={
            "name": "Journal of Applied Plasma Engineering",
            "publisher": "Example Press",
            "issn_print": "1111-2222",
            "keywords": {"mode": "and", "terms": ["plasma", "etching"]},
            "year_from": 2001,
        },
    )

    assert created.status_code == 201
    journal = created.json()
    assert journal["keywords"] == {"mode": "and", "terms": ["plasma", "etching"]}
    assert journal["active"] is True

    listed = client.get("/api/v1/journals", params={"active": "true", "page_size": 100}).json()
    assert listed["total"] == 7
    assert any(item["id"] == journal["id"] for item in listed["items"])

    updated = client.put(
        f"/api/v1/journals/{journal['id']}",
        json={"keywords": {"mode": "or", "terms": ["plasma chemistry"]}, "active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["keywords"] == {"mode": "or", "terms": ["plasma chemistry"]}
    assert updated.json()["active"] is False

    active_only = client.get("/api/v1/journals", params={"active": "true", "page_size": 100}).json()
    assert active_only["total"] == 6
    assert all(item["id"] != journal["id"] for item in active_only["items"])

    deleted = client.delete(f"/api/v1/journals/{journal['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["active"] is False

    missing = client.put("/api/v1/journals/9999", json={"active": False})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "journal_not_found"


def test_journal_normalizes_issn_fields_for_crawl_lookup(tmp_path):
    client = make_client(tmp_path)

    created = client.post(
        "/api/v1/journals",
        json={
            "name": "ISSN Normalization Journal",
            "issn_print": " 1234-567x ",
            "issn_electronic": " 9876-5432 ",
            "keywords": ["plasma"],
        },
    )

    assert created.status_code == 201
    journal = created.json()
    assert journal["issn_print"] == "1234-567X"
    assert journal["issn_electronic"] == "9876-5432"

    updated = client.put(
        f"/api/v1/journals/{journal['id']}",
        json={"issn_print": " 1111-222x "},
    )

    assert updated.status_code == 200
    assert updated.json()["issn_print"] == "1111-222X"


def test_journal_rejects_invalid_issn_fields(tmp_path):
    client = make_client(tmp_path)

    created = client.post(
        "/api/v1/journals",
        json={"name": "Invalid ISSN Journal", "issn_print": "12345678"},
    )
    existing = client.post(
        "/api/v1/journals",
        json={"name": "Valid ISSN Journal", "issn_print": "1234-567X"},
    ).json()
    updated = client.put(
        f"/api/v1/journals/{existing['id']}",
        json={"issn_electronic": "not-an-issn"},
    )

    assert created.status_code == 422
    assert created.json()["error"]["code"] == "validation_error"
    assert updated.status_code == 422
    assert updated.json()["error"]["code"] == "validation_error"


def test_journal_keywords_reject_invalid_config(tmp_path):
    client = make_client(tmp_path)

    invalid_mode = client.post(
        "/api/v1/journals",
        json={"name": "Invalid Keyword Mode", "keywords": {"mode": "xor", "terms": ["plasma"]}},
    )
    empty_terms = client.post(
        "/api/v1/journals",
        json={"name": "Invalid Keyword Terms", "keywords": {"mode": "and", "terms": []}},
    )

    assert invalid_mode.status_code == 422
    assert invalid_mode.json()["error"]["code"] == "validation_error"
    assert empty_terms.status_code == 422
    assert empty_terms.json()["error"]["code"] == "validation_error"


def test_journal_year_range_rejects_reversed_bounds(tmp_path):
    client = make_client(tmp_path)

    created = client.post(
        "/api/v1/journals",
        json={"name": "Invalid Years", "year_from": 2030, "year_to": 2020},
    )
    existing = client.post(
        "/api/v1/journals",
        json={"name": "Valid Years", "year_from": 2000, "year_to": 2020},
    ).json()
    updated = client.put(
        f"/api/v1/journals/{existing['id']}",
        json={"year_from": 2030, "year_to": 2020},
    )

    assert created.status_code == 422
    assert created.json()["error"]["code"] == "validation_error"
    assert updated.status_code == 422
    assert updated.json()["error"]["code"] == "validation_error"


def test_journal_update_rejects_reversed_bounds_against_existing_values(tmp_path):
    client = make_client(tmp_path)

    existing = client.post(
        "/api/v1/journals",
        json={"name": "Partial Year Update", "year_from": 2000, "year_to": 2020},
    ).json()

    invalid_to = client.put(
        f"/api/v1/journals/{existing['id']}",
        json={"year_to": 1999},
    )
    invalid_from = client.put(
        f"/api/v1/journals/{existing['id']}",
        json={"year_from": 2021},
    )

    assert invalid_to.status_code == 422
    assert invalid_to.json()["error"]["code"] == "validation_error"
    assert invalid_from.status_code == 422
    assert invalid_from.json()["error"]["code"] == "validation_error"


def test_journal_rejects_blank_name(tmp_path):
    client = make_client(tmp_path)

    created = client.post("/api/v1/journals", json={"name": "   "})
    existing = client.post("/api/v1/journals", json={"name": "Valid Journal"}).json()
    updated = client.put(f"/api/v1/journals/{existing['id']}", json={"name": "   "})

    assert created.status_code == 422
    assert created.json()["error"]["code"] == "validation_error"
    assert updated.status_code == 422
    assert updated.json()["error"]["code"] == "validation_error"


def test_categories_list_includes_total_and_direct_children(tmp_path):
    client = make_client(tmp_path)

    parent = client.post(
        "/api/v1/categories",
        json={"name": "Surface Chemistry", "slug": "surface-chemistry"},
    ).json()
    child = client.post(
        "/api/v1/categories",
        json={
            "name": "Etch Products",
            "slug": "etch-products",
            "parent_id": parent["id"],
        },
    ).json()

    categories = client.get("/api/v1/categories").json()
    assert categories["total"] == 9
    assert categories["page"] == 1
    assert categories["page_size"] == 9

    parent_item = next(item for item in categories["items"] if item["id"] == parent["id"])
    assert parent_item["children"] == [child]
    child_item = next(item for item in categories["items"] if item["id"] == child["id"])
    assert child_item["children"] == []


def test_create_category_rejects_blank_name_and_slug(tmp_path):
    client = make_client(tmp_path)

    blank_name = client.post(
        "/api/v1/categories",
        json={"name": "   ", "slug": "blank-name"},
    )
    blank_slug = client.post(
        "/api/v1/categories",
        json={"name": "Blank Slug", "slug": "   "},
    )

    assert blank_name.status_code == 422
    assert blank_name.json()["error"]["code"] == "validation_error"
    assert blank_slug.status_code == 422
    assert blank_slug.json()["error"]["code"] == "validation_error"


def test_create_category_normalizes_slug_for_taxonomy_consistency(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/categories",
        json={"name": "Surface Chemistry", "slug": "  Surface-Chemistry  "},
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "surface-chemistry"
    categories = client.get("/api/v1/categories").json()["items"]
    created = next(item for item in categories if item["name"] == "Surface Chemistry")
    assert created["slug"] == "surface-chemistry"


def test_create_category_normalizes_slug_whitespace_to_hyphen(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/categories",
        json={"name": "Plasma Transport", "slug": "  Plasma Transport  "},
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "plasma-transport"


def test_create_category_rejects_path_like_slug(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/categories",
        json={"name": "Bad Slug", "slug": "bad/slug"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_category_with_unknown_parent_returns_json_error(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/categories",
        json={"name": "Unknown Parent Child", "slug": "unknown-parent-child", "parent_id": 9999},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "category_parent_not_found"


def test_unhandled_exceptions_return_contract_json_error():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.errors import install_error_handlers

    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise RuntimeError("unexpected backend failure")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "Internal server error",
        }
    }


def test_document_related_lists_use_page_query_and_metadata(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        for idx in range(3):
            conn.execute(
                """
                INSERT INTO documents (file_path, file_hash, original_name, parse_status)
                VALUES (?, ?, ?, 'parsed')
                """,
                (f"/tmp/doc-{idx}.pdf", f"hash-{idx}", f"doc-{idx}.pdf"),
            )
        doc_ids = [row["id"] for row in conn.execute("SELECT id FROM documents ORDER BY id").fetchall()]
        document_id = doc_ids[0]
        for seq in range(3):
            conn.execute(
                """
                INSERT INTO sections (document_id, seq, title, content, section_type)
                VALUES (?, ?, ?, ?, 'body')
                """,
                (document_id, seq, f"Section {seq}", f"Content {seq}"),
            )
            conn.execute(
                """
                INSERT INTO chunks (document_id, seq, text, token_count, vector_id, embedded)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (document_id, seq, f"Chunk {seq}", 2, f"vec-{seq}"),
            )
            conn.execute(
                """
                INSERT INTO reaction_sets (document_id, name, status)
                VALUES (?, ?, 'pending')
                """,
                (document_id, f"Set {seq}"),
            )

    documents = client.get("/api/v1/documents", params={"page": 2, "page_size": 1}).json()
    assert documents["total"] == 3
    assert documents["page"] == 2
    assert documents["page_size"] == 1
    assert documents["items"][0]["id"] == doc_ids[1]

    sections = client.get(f"/api/v1/documents/{document_id}/sections", params={"page": 2, "page_size": 1}).json()
    assert sections["total"] == 3
    assert sections["page"] == 2
    assert sections["page_size"] == 1
    assert sections["items"][0]["title"] == "Section 1"

    chunks = client.get(f"/api/v1/documents/{document_id}/chunks", params={"page": 3, "page_size": 1}).json()
    assert chunks["total"] == 3
    assert chunks["page"] == 3
    assert chunks["page_size"] == 1
    assert chunks["items"][0]["vector_id"] == "vec-2"

    reaction_sets = client.get(
        f"/api/v1/documents/{document_id}/reaction-sets",
        params={"page": 2, "page_size": 1},
    ).json()
    assert reaction_sets["total"] == 3
    assert reaction_sets["page"] == 2
    assert reaction_sets["page_size"] == 1
    assert reaction_sets["items"][0]["name"] == "Set 1"


def test_document_responses_include_linked_paper_summary(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        paper_id = conn.execute(
            """
            INSERT INTO papers (
                doi, title, abstract, authors, journal_name,
                published_date, published_year, source_api, raw_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "10.1/document-link",
                "Linked plasma document",
                "argon plasma",
                "[]",
                "Plasma Sources Science and Technology",
                "2026-06-01",
                2026,
                "fixture",
                "{}",
            ),
        ).lastrowid

    created = client.post(
        "/api/v1/documents",
        data={"paper_id": str(paper_id)},
        files={"file": ("linked.pdf", pdf_bytes(b"Linked paper PDF"), "application/pdf")},
    )

    assert created.status_code == 201
    document = created.json()
    expected_paper = {
        "id": paper_id,
        "doi": "10.1/document-link",
        "title": "Linked plasma document",
        "journal_name": "Plasma Sources Science and Technology",
        "published_date": "2026-06-01",
    }
    assert document["paper_id"] == paper_id
    assert document["paper"] == expected_paper

    detail = client.get(f"/api/v1/documents/{document['id']}").json()
    assert detail["paper"] == expected_paper

    listed = client.get("/api/v1/documents").json()["items"][0]
    assert listed["paper"] == expected_paper


def test_duplicate_document_upload_returns_existing_resource(tmp_path):
    client = make_client(tmp_path)

    first = client.post(
        "/api/v1/documents",
        files={"file": ("duplicate.pdf", pdf_bytes(b"Argon plasma chemistry"), "application/pdf")},
    )
    duplicate = client.post(
        "/api/v1/documents",
        files={"file": ("duplicate-again.pdf", pdf_bytes(b"Argon plasma chemistry"), "application/pdf")},
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    payload = duplicate.json()
    assert payload["error"]["code"] == "document_duplicate"
    assert payload["document"]["id"] == first.json()["id"]
    assert payload["document"]["file_hash"] == first.json()["file_hash"]
    assert payload["document"]["original_name"] == "duplicate.pdf"


def test_document_upload_stores_pdf_with_pdf_extension_even_when_filename_is_misleading(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("misleading.txt", pdf_bytes(b"Argon plasma chemistry"), "application/pdf")},
    )

    assert response.status_code == 201
    document = response.json()
    assert document["original_name"] == "misleading.txt"
    assert document["file_path"].endswith(".pdf")
    assert Path(document["file_path"]).suffix == ".pdf"


def test_document_upload_records_pdf_page_count(tmp_path):
    client = make_client(tmp_path)
    content = pdf_bytes(
        b"1 0 obj << /Type /Page >> endobj\n"
        b"2 0 obj << /Type /Pages /Count 2 >> endobj\n"
        b"3 0 obj << /Type /Page >> endobj\n"
    )

    response = client.post(
        "/api/v1/documents",
        files={"file": ("two-pages.pdf", content, "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["num_pages"] == 2


def test_document_upload_rejects_non_pdf_file(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", b"plain text is not a pdf", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_document_type"


def test_document_upload_rejects_pdf_claim_with_invalid_magic_header(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("fake.pdf", b"plain text is not a pdf", "application/pdf")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_document_type"


def test_document_upload_with_unknown_paper_id_returns_json_error(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/documents",
        data={"paper_id": "9999"},
        files={"file": ("orphan.pdf", pdf_bytes(b"orphan document"), "application/pdf")},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "paper_not_found"


def test_rag_query_rejects_empty_question_and_invalid_top_k(tmp_path):
    client = make_client(tmp_path)

    empty_question = client.post("/api/v1/rag/query", json={"question": "   ", "top_k": 3})
    invalid_top_k = client.post("/api/v1/rag/query", json={"question": "argon plasma", "top_k": 0})
    invalid_document_ids = client.post(
        "/api/v1/rag/query",
        json={"question": "argon plasma", "document_ids": [1, 0, -2], "top_k": 3},
    )

    assert empty_question.status_code == 422
    assert empty_question.json()["error"]["code"] == "validation_error"
    assert invalid_top_k.status_code == 422
    assert invalid_top_k.json()["error"]["code"] == "validation_error"
    assert invalid_document_ids.status_code == 422
    assert invalid_document_ids.json()["error"]["code"] == "validation_error"


def test_rag_query_rejects_unknown_document_id(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/rag/query",
        json={"question": "argon plasma", "document_ids": [999], "top_k": 3},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "document_not_found"
    assert "999" in response.json()["error"]["message"]


def test_rag_query_backend_failure_returns_json_error(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    (tmp_path / "vector-index.json").write_text("{not valid json", encoding="utf-8")
    with get_conn() as conn:
        document_id = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status, index_status)
            VALUES (?, ?, ?, 'parsed', 'indexed')
            """,
            ("/tmp/rag-query-corrupt-vector.txt", "rag-query-corrupt-vector", "rag-query-corrupt-vector.txt"),
        ).lastrowid

    response = client.post(
        "/api/v1/rag/query",
        json={"question": "argon plasma", "document_ids": [document_id], "top_k": 3},
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "rag_query_failed"
    assert "vector store JSON is invalid" in payload["error"]["message"]


def test_fixture_loader_supports_walking_skeleton(tmp_path):
    client = make_client(tmp_path)

    from app.fixture_loader import load_fixture_papers

    result = load_fixture_papers()
    assert result["inserted"] == 2
    papers = client.get("/api/v1/papers?q=plasma").json()
    assert papers["total"] >= 2
    oa_only = client.get("/api/v1/papers?q=plasma&oa_only=true").json()
    assert oa_only["total"] == 1
    repeat = load_fixture_papers()
    assert repeat["updated"] == 2


def test_fixture_loader_imports_idempotent_document_sample(tmp_path):
    client = make_client(tmp_path)

    from app.fixture_loader import load_fixture_documents, load_fixture_papers

    load_fixture_papers()
    first = load_fixture_documents()
    repeat = load_fixture_documents()

    assert first["inserted"] == 1
    assert first["updated"] == 0
    assert repeat["inserted"] == 0
    assert repeat["updated"] == 1

    documents = client.get("/api/v1/documents").json()
    assert documents["total"] == 1
    document = documents["items"][0]
    assert document["original_name"] == "fixture-plasma-chemistry.pdf"
    assert document["parse_status"] == "uploaded"
    assert Path(document["file_path"]).exists()
    assert document["paper"]["doi"] == "10.1088/1361-6595/fixture-ar-o2"


def test_fixture_import_script_runs_from_repo_root(tmp_path):
    import json
    import sqlite3
    import subprocess
    import sys

    env = os.environ.copy()
    env["DATABASE_PATH"] = str(tmp_path / "script.db")
    env["PAPER_LAB_DATA_DIR"] = str(tmp_path)
    for key in [
        "PAPER_LAB_PDF_DIR",
        "PAPER_LAB_TEI_DIR",
        "PAPER_LAB_TRANSLATION_DIR",
        "PAPER_LAB_EXPORT_DIR",
        "VECTOR_DB_PATH",
    ]:
        env.pop(key, None)
    result = subprocess.run(
        [sys.executable, "scripts/import_fixtures.py"],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["papers"]["inserted"] == 2
    assert payload["documents"]["inserted"] == 1
    with sqlite3.connect(tmp_path / "script.db") as conn:
        conn.row_factory = sqlite3.Row
        document = conn.execute("SELECT file_path FROM documents").fetchone()
    assert document is not None
    assert Path(document["file_path"]).resolve().is_relative_to(tmp_path.resolve())


def test_smoke_check_covers_translation_and_chemistry_chain():
    from scripts.smoke_check import run_smoke

    result = run_smoke()

    assert result["crawl_jobs"] >= 1
    assert result["crawl_job_status"] == "success"
    assert result["crawl_job_found"] >= 1
    assert result["crawl_job_filtered"] >= 0
    assert result["crawl_job_new"] >= 1
    assert result["crawled_papers"] >= 1
    assert result["papers"] == 2
    assert result["paper_categories"] == 1
    assert result["duplicate_upload_status"] == 409
    assert result["duplicate_document_id"] == result["document_id"]
    assert result["translation_status"] == "done"
    assert result["sections"] == 1
    assert result["chunks"] == 1
    assert result["rag_sources"] == 1
    assert result["reaction_sets"] == 1
    assert result["reactions"] == 1
    assert result["blocked_export_status"] == 409
    assert result["verified_export_format"] == "json"
    assert result["verified_export_formats"] == ["json", "txt", "bolsig"]
    assert result["verified_export_reactions"] == 1
    assert result["verified_export_audit_entries"] >= 1
    assert result["verified_export_response_reactions"] == 1
    assert result["verified_export_response_audit_entries"] >= 1
    assert result["verified_export_source_sections"] == 1
    assert result["verified_export_text_files"] == 2
    assert result["verified_export_bolsig_contains_header"] is True
    assert result["verified_export_txt_contains_reaction"] is True
    assert result["verified_export_txt_has_source_excerpt"] is True
    assert result["rag_answer_has_citation"] is True
    assert result["rag_source_excerpts"] == 1
    assert result["verified_export_txt_has_verification_metadata"] is True
    assert result["verified_export_bolsig_has_verification_metadata"] is True
    assert result["translation_output_path"].endswith("document-1-zh.md")
    assert result["verified_export_path"].endswith("reaction-set-1.json")
    assert result["runtime_version"] == "0.1.0"
    assert result["scheduler_job_ids"] == ["crawl-daily", "crawl-weekly", "crawl-monthly"]
    assert result["config_warning_count"] == 3


def test_smoke_check_script_outputs_json():
    import json
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "scripts.smoke_check"],
        cwd=Path(__file__).resolve().parent.parent,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(result.stdout)
    assert payload["crawl_jobs"] >= 1
    assert payload["crawl_job_status"] == "success"
    assert payload["crawled_papers"] >= 1
    assert payload["papers"] == 2
    assert payload["paper_categories"] == 1
    assert payload["duplicate_upload_status"] == 409
    assert payload["translation_status"] == "done"
    assert payload["sections"] == 1
    assert payload["chunks"] == 1
    assert payload["rag_sources"] == 1
    assert payload["blocked_export_status"] == 409
    assert payload["verified_export_format"] == "json"
    assert payload["verified_export_formats"] == ["json", "txt", "bolsig"]
    assert payload["verified_export_reactions"] == 1
    assert payload["verified_export_audit_entries"] >= 1
    assert payload["verified_export_response_reactions"] == 1
    assert payload["verified_export_response_audit_entries"] >= 1
    assert payload["verified_export_text_files"] == 2
    assert payload["verified_export_bolsig_contains_header"] is True
    assert payload["verified_export_txt_contains_reaction"] is True
    assert payload["verified_export_txt_has_source_excerpt"] is True
    assert payload["rag_answer_has_citation"] is True
    assert payload["rag_source_excerpts"] == 1
    assert payload["verified_export_txt_has_verification_metadata"] is True
    assert payload["verified_export_bolsig_has_verification_metadata"] is True
    assert payload["runtime_version"] == "0.1.0"
    assert payload["scheduler_job_ids"] == ["crawl-daily", "crawl-weekly", "crawl-monthly"]
    assert payload["config_warning_count"] == 3


def test_migrations_add_lxcat_db_to_legacy_reaction_sets():
    import sqlite3

    from app.db import ensure_migrations

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE crawl_jobs (id INTEGER PRIMARY KEY);
        CREATE TABLE papers (id INTEGER PRIMARY KEY);
        CREATE TABLE documents (id INTEGER PRIMARY KEY);
        CREATE TABLE sections (id INTEGER PRIMARY KEY);
        CREATE TABLE translations (id INTEGER PRIMARY KEY);
        CREATE TABLE reaction_sets (
            id INTEGER PRIMARY KEY,
            document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
            name TEXT,
            gas_mixture TEXT,
            source_note TEXT,
            status TEXT DEFAULT 'pending',
            verified_by TEXT,
            verified_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY,
            reaction_set_id INTEGER NOT NULL REFERENCES reaction_sets(id) ON DELETE CASCADE,
            reaction TEXT NOT NULL
        );
        """
    )

    ensure_migrations(conn)

    reaction_set_columns = {row["name"] for row in conn.execute("PRAGMA table_info(reaction_sets)").fetchall()}
    reaction_columns = {row["name"] for row in conn.execute("PRAGMA table_info(reactions)").fetchall()}
    reaction_audits = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='reaction_audits'"
    ).fetchone()

    assert "lxcat_db" in reaction_set_columns
    for column in [
        "reaction_type",
        "reactants",
        "products",
        "rate_type",
        "rate_value",
        "threshold_ev",
        "reference",
        "cross_section_url",
        "source_section_id",
        "source_excerpt",
        "confidence",
        "verified",
        "created_at",
    ]:
        assert column in reaction_columns
    assert reaction_audits is not None


def test_migrations_create_and_rebuild_papers_fts_for_legacy_database():
    import sqlite3

    from app.db import ensure_migrations

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE journals (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE papers (
            id INTEGER PRIMARY KEY,
            doi TEXT,
            title TEXT NOT NULL,
            abstract TEXT,
            authors TEXT,
            journal_id INTEGER REFERENCES journals(id),
            journal_name TEXT,
            published_date TEXT,
            published_year INTEGER,
            landing_url TEXT,
            oa_status TEXT,
            oa_pdf_url TEXT,
            source_api TEXT,
            raw_metadata TEXT,
            indexed_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE crawl_jobs (id INTEGER PRIMARY KEY);
        CREATE TABLE documents (id INTEGER PRIMARY KEY);
        CREATE TABLE sections (id INTEGER PRIMARY KEY);
        CREATE TABLE translations (id INTEGER PRIMARY KEY);
        CREATE TABLE reaction_sets (id INTEGER PRIMARY KEY);
        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY,
            reaction_set_id INTEGER NOT NULL REFERENCES reaction_sets(id) ON DELETE CASCADE,
            reaction TEXT NOT NULL
        );
        INSERT INTO papers (title, abstract, authors, raw_metadata)
        VALUES ('Legacy argon plasma paper', 'metastable electron chemistry', '[]', '{}');
        """
    )

    ensure_migrations(conn)

    fts = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='papers_fts'").fetchone()
    triggers = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name IN ('papers_ai','papers_ad','papers_au')"
        ).fetchall()
    }
    rows = conn.execute(
        """
        SELECT p.id
        FROM papers_fts fts
        JOIN papers p ON p.id = fts.rowid
        WHERE papers_fts MATCH ?
        """,
        ("metastable",),
    ).fetchall()

    assert fts is not None
    assert triggers == {"papers_ai", "papers_ad", "papers_au"}
    assert [row["id"] for row in rows] == [1]


def test_migrations_repair_existing_papers_fts_without_triggers():
    import sqlite3

    from app.db import ensure_migrations

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE journals (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE papers (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            abstract TEXT
        );
        CREATE VIRTUAL TABLE papers_fts USING fts5(
            title, abstract,
            content='papers', content_rowid='id',
            tokenize='unicode61'
        );
        CREATE TABLE crawl_jobs (id INTEGER PRIMARY KEY);
        CREATE TABLE documents (id INTEGER PRIMARY KEY);
        CREATE TABLE sections (id INTEGER PRIMARY KEY);
        CREATE TABLE translations (id INTEGER PRIMARY KEY);
        CREATE TABLE reaction_sets (id INTEGER PRIMARY KEY);
        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY,
            reaction_set_id INTEGER NOT NULL REFERENCES reaction_sets(id) ON DELETE CASCADE,
            reaction TEXT NOT NULL
        );
        INSERT INTO papers (title, abstract)
        VALUES ('Legacy oxygen plasma paper', 'ion transport kinetics');
        """
    )

    ensure_migrations(conn)

    triggers = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name IN ('papers_ai','papers_ad','papers_au')"
        ).fetchall()
    }
    existing_rows = conn.execute(
        """
        SELECT p.id
        FROM papers_fts fts
        JOIN papers p ON p.id = fts.rowid
        WHERE papers_fts MATCH ?
        """,
        ("kinetics",),
    ).fetchall()
    conn.execute("INSERT INTO papers (title, abstract) VALUES (?, ?)", ("New argon plasma paper", "metastable chemistry"))
    inserted_rows = conn.execute(
        """
        SELECT p.title
        FROM papers_fts fts
        JOIN papers p ON p.id = fts.rowid
        WHERE papers_fts MATCH ?
        """,
        ("metastable",),
    ).fetchall()

    assert triggers == {"papers_ai", "papers_ad", "papers_au"}
    assert [row["id"] for row in existing_rows] == [1]
    assert [row["title"] for row in inserted_rows] == ["New argon plasma paper"]


def test_migrations_add_missing_paper_columns_for_minimal_legacy_table():
    import sqlite3

    from app.db import ensure_migrations

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE journals (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE papers (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            abstract TEXT
        );
        CREATE TABLE crawl_jobs (id INTEGER PRIMARY KEY);
        CREATE TABLE documents (id INTEGER PRIMARY KEY);
        CREATE TABLE sections (id INTEGER PRIMARY KEY);
        CREATE TABLE translations (id INTEGER PRIMARY KEY);
        CREATE TABLE reaction_sets (id INTEGER PRIMARY KEY);
        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY,
            reaction_set_id INTEGER NOT NULL REFERENCES reaction_sets(id) ON DELETE CASCADE,
            reaction TEXT NOT NULL
        );
        INSERT INTO papers (title, abstract) VALUES ('Minimal legacy plasma', 'argon chemistry');
        """
    )

    ensure_migrations(conn)

    paper_columns = {row["name"] for row in conn.execute("PRAGMA table_info(papers)").fetchall()}
    conn.execute(
        """
        INSERT INTO papers (
            doi, title, abstract, authors, journal_id, journal_name,
            published_date, published_year, landing_url, oa_status,
            oa_pdf_url, source_api, raw_metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "10.legacy/minimal",
            "Migrated paper",
            "electron kinetics",
            "[]",
            None,
            "Migrated Journal",
            "2026-01-01",
            2026,
            "https://example.test",
            "unknown",
            None,
            "fixture",
            "{}",
        ),
    )
    rows = conn.execute(
        """
        SELECT p.title
        FROM papers_fts fts
        JOIN papers p ON p.id = fts.rowid
        WHERE papers_fts MATCH ?
        ORDER BY p.id
        """,
        ("electron",),
    ).fetchall()

    assert {
        "doi",
        "authors",
        "journal_id",
        "journal_name",
        "published_date",
        "published_year",
        "landing_url",
        "oa_status",
        "oa_pdf_url",
        "source_api",
        "dedupe_key",
        "raw_metadata",
        "indexed_at",
        "updated_at",
    }.issubset(paper_columns)
    assert [row["title"] for row in rows] == ["Migrated paper"]


def test_migrations_skip_paper_dedupe_unique_index_when_legacy_duplicates_exist():
    import sqlite3

    from app.db import ensure_migrations

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE journals (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE papers (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            abstract TEXT,
            dedupe_key TEXT
        );
        CREATE TABLE crawl_jobs (id INTEGER PRIMARY KEY);
        CREATE TABLE documents (id INTEGER PRIMARY KEY);
        CREATE TABLE sections (id INTEGER PRIMARY KEY);
        CREATE TABLE translations (id INTEGER PRIMARY KEY);
        CREATE TABLE reaction_sets (id INTEGER PRIMARY KEY);
        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY,
            reaction_set_id INTEGER NOT NULL REFERENCES reaction_sets(id) ON DELETE CASCADE,
            reaction TEXT NOT NULL
        );
        INSERT INTO papers (title, abstract, dedupe_key)
        VALUES
            ('Duplicate paper A', 'argon plasma', 'legacy-dup'),
            ('Duplicate paper B', 'argon plasma update', 'legacy-dup');
        """
    )

    ensure_migrations(conn)

    indexes_with_duplicates = {
        index["name"]: [
            row["name"] for row in conn.execute(f"PRAGMA index_info({index['name']})").fetchall()
        ]
        for index in conn.execute("PRAGMA index_list(papers)").fetchall()
        if index["unique"]
    }
    conn.execute("UPDATE papers SET dedupe_key='legacy-dup-b' WHERE title='Duplicate paper B'")
    ensure_migrations(conn)
    indexes_after_cleanup = {
        index["name"]: [
            row["name"] for row in conn.execute(f"PRAGMA index_info({index['name']})").fetchall()
        ]
        for index in conn.execute("PRAGMA index_list(papers)").fetchall()
        if index["unique"]
    }

    assert ["dedupe_key"] not in indexes_with_duplicates.values()
    assert ["dedupe_key"] in indexes_after_cleanup.values()


def test_migrations_add_missing_crawl_job_columns_for_legacy_table():
    import sqlite3

    from app.db import ensure_migrations

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE journals (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE papers (id INTEGER PRIMARY KEY, title TEXT NOT NULL, abstract TEXT);
        CREATE TABLE crawl_jobs (id INTEGER PRIMARY KEY);
        CREATE TABLE documents (id INTEGER PRIMARY KEY);
        CREATE TABLE sections (id INTEGER PRIMARY KEY);
        CREATE TABLE translations (id INTEGER PRIMARY KEY);
        CREATE TABLE reaction_sets (id INTEGER PRIMARY KEY);
        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY,
            reaction_set_id INTEGER NOT NULL REFERENCES reaction_sets(id) ON DELETE CASCADE,
            reaction TEXT NOT NULL
        );
        INSERT INTO journals (id, name) VALUES (1, 'Legacy Journal');
        """
    )

    ensure_migrations(conn)

    crawl_job_columns = {row["name"] for row in conn.execute("PRAGMA table_info(crawl_jobs)").fetchall()}
    conn.execute(
        """
        INSERT INTO crawl_jobs (
            journal_id, period, date_from, date_to, status,
            papers_found, papers_filtered, papers_new, error, started_at, finished_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (1, "manual", "2026-01-01", "2026-01-02", "success", 4, 1, 3, None, "2026-01-01", "2026-01-02"),
    )
    row = conn.execute("SELECT * FROM crawl_jobs WHERE journal_id=1").fetchone()

    assert {
        "journal_id",
        "period",
        "date_from",
        "date_to",
        "status",
        "papers_found",
        "papers_filtered",
        "papers_new",
        "error",
        "started_at",
        "finished_at",
        "created_at",
    }.issubset(crawl_job_columns)
    assert row["papers_found"] == 4
    assert row["papers_filtered"] == 1
    assert row["papers_new"] == 3


def test_migrations_add_missing_document_columns_for_legacy_table():
    import sqlite3

    from app.db import ensure_migrations

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE journals (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE papers (id INTEGER PRIMARY KEY, title TEXT NOT NULL, abstract TEXT);
        CREATE TABLE crawl_jobs (id INTEGER PRIMARY KEY);
        CREATE TABLE documents (id INTEGER PRIMARY KEY, file_path TEXT NOT NULL);
        CREATE TABLE sections (id INTEGER PRIMARY KEY);
        CREATE TABLE translations (id INTEGER PRIMARY KEY);
        CREATE TABLE reaction_sets (id INTEGER PRIMARY KEY);
        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY,
            reaction_set_id INTEGER NOT NULL REFERENCES reaction_sets(id) ON DELETE CASCADE,
            reaction TEXT NOT NULL
        );
        """
    )

    ensure_migrations(conn)

    document_columns = {row["name"] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
    conn.execute(
        """
        INSERT INTO documents (
            paper_id, file_path, file_hash, original_name, num_pages,
            parse_status, parse_error, index_status, index_error,
            chemistry_status, chemistry_error, tei_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            None,
            "/tmp/doc.pdf",
            "hash-1",
            "doc.pdf",
            3,
            "uploaded",
            None,
            "not_indexed",
            None,
            "not_extracted",
            None,
            None,
        ),
    )
    row = conn.execute("SELECT * FROM documents WHERE file_hash='hash-1'").fetchone()
    indexes = {
        index["name"]
        for index in conn.execute("PRAGMA index_list(documents)").fetchall()
        if index["unique"]
    }

    assert {
        "paper_id",
        "file_path",
        "file_hash",
        "original_name",
        "num_pages",
        "parse_status",
        "parse_error",
        "index_status",
        "index_error",
        "chemistry_status",
        "chemistry_error",
        "tei_path",
        "created_at",
    }.issubset(document_columns)
    assert row["original_name"] == "doc.pdf"
    assert row["index_status"] == "not_indexed"
    assert row["chemistry_status"] == "not_extracted"
    assert indexes


def test_migrations_add_missing_understanding_layer_columns_for_legacy_tables():
    import sqlite3

    from app.db import ensure_migrations

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE journals (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE papers (id INTEGER PRIMARY KEY, title TEXT NOT NULL, abstract TEXT);
        CREATE TABLE crawl_jobs (id INTEGER PRIMARY KEY);
        CREATE TABLE documents (id INTEGER PRIMARY KEY, file_path TEXT NOT NULL);
        CREATE TABLE sections (id INTEGER PRIMARY KEY);
        CREATE TABLE translations (id INTEGER PRIMARY KEY);
        CREATE TABLE chunks (id INTEGER PRIMARY KEY);
        CREATE TABLE reaction_sets (id INTEGER PRIMARY KEY);
        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY,
            reaction_set_id INTEGER NOT NULL REFERENCES reaction_sets(id) ON DELETE CASCADE,
            reaction TEXT NOT NULL
        );
        """
    )

    ensure_migrations(conn)

    conn.execute(
        "INSERT INTO documents (file_path, file_hash, parse_status) VALUES (?, ?, ?)",
        ("/tmp/doc.pdf", "hash-1", "parsed"),
    )
    document_id = conn.execute("SELECT id FROM documents WHERE file_hash='hash-1'").fetchone()["id"]
    conn.execute(
        """
        INSERT INTO sections (document_id, parent_id, seq, title, content, section_type)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (document_id, None, 1, "Abstract", "Plasma chemistry", "abstract"),
    )
    section_id = conn.execute("SELECT id FROM sections WHERE document_id=?", (document_id,)).fetchone()["id"]
    conn.execute(
        """
        INSERT INTO translations (document_id, source_lang, target_lang, status, output_path, error)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (document_id, "en", "zh", "done", "/tmp/doc.zh.md", None),
    )
    conn.execute(
        """
        INSERT INTO chunks (document_id, section_id, seq, text, token_count, vector_id, embedded)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (document_id, section_id, 1, "Plasma chemistry", 2, "vec-1", 1),
    )
    conn.execute(
        """
        INSERT INTO reaction_sets (
            document_id, name, gas_mixture, lxcat_db, source_note,
            status, verified_by, verified_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (document_id, "Set 1", "Ar/O2", "Phelps", "Table 1", "pending", None, None),
    )

    section_columns = {row["name"] for row in conn.execute("PRAGMA table_info(sections)").fetchall()}
    translation_columns = {row["name"] for row in conn.execute("PRAGMA table_info(translations)").fetchall()}
    chunk_columns = {row["name"] for row in conn.execute("PRAGMA table_info(chunks)").fetchall()}
    reaction_set_columns = {row["name"] for row in conn.execute("PRAGMA table_info(reaction_sets)").fetchall()}
    indexes = {
        row["name"]
        for row in conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='index' AND name IN (
                'idx_sections_doc', 'idx_translations_doc', 'idx_chunks_doc', 'idx_rsets_doc'
            )
            """
        ).fetchall()
    }

    assert {"document_id", "parent_id", "seq", "title", "content", "section_type"}.issubset(section_columns)
    assert {"document_id", "source_lang", "target_lang", "status", "output_path", "error", "created_at"}.issubset(
        translation_columns
    )
    assert {"document_id", "section_id", "seq", "text", "token_count", "vector_id", "embedded", "created_at"}.issubset(
        chunk_columns
    )
    assert {
        "document_id",
        "name",
        "gas_mixture",
        "lxcat_db",
        "source_note",
        "status",
        "verified_by",
        "verified_at",
        "created_at",
    }.issubset(reaction_set_columns)
    assert indexes == {"idx_sections_doc", "idx_translations_doc", "idx_chunks_doc", "idx_rsets_doc"}


def test_migrations_add_missing_taxonomy_and_audit_columns_for_legacy_tables():
    import sqlite3

    from app.db import ensure_migrations

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE journals (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
        CREATE TABLE papers (id INTEGER PRIMARY KEY, title TEXT NOT NULL, abstract TEXT);
        CREATE TABLE categories (id INTEGER PRIMARY KEY);
        CREATE TABLE paper_categories (id INTEGER PRIMARY KEY);
        CREATE TABLE crawl_jobs (id INTEGER PRIMARY KEY);
        CREATE TABLE documents (id INTEGER PRIMARY KEY, file_path TEXT NOT NULL);
        CREATE TABLE sections (id INTEGER PRIMARY KEY);
        CREATE TABLE translations (id INTEGER PRIMARY KEY);
        CREATE TABLE chunks (id INTEGER PRIMARY KEY);
        CREATE TABLE reaction_sets (id INTEGER PRIMARY KEY);
        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY,
            reaction_set_id INTEGER NOT NULL REFERENCES reaction_sets(id) ON DELETE CASCADE,
            reaction TEXT NOT NULL
        );
        CREATE TABLE reaction_audits (id INTEGER PRIMARY KEY);
        """
    )

    ensure_migrations(conn)

    conn.execute("INSERT INTO papers (title, abstract) VALUES (?, ?)", ("Paper 1", "Abstract"))
    paper_id = conn.execute("SELECT id FROM papers WHERE title='Paper 1'").fetchone()["id"]
    conn.execute(
        "INSERT INTO categories (name, slug, description, parent_id) VALUES (?, ?, ?, ?)",
        ("Plasma chemistry", "plasma-chemistry", "Reactions", None),
    )
    category_id = conn.execute("SELECT id FROM categories WHERE slug='plasma-chemistry'").fetchone()["id"]
    conn.execute(
        """
        INSERT INTO paper_categories (paper_id, category_id, confidence, method)
        VALUES (?, ?, ?, ?)
        """,
        (paper_id, category_id, 0.87, "auto"),
    )
    conn.execute("INSERT INTO reaction_sets (name, status) VALUES (?, ?)", ("Set 1", "pending"))
    reaction_set_id = conn.execute("SELECT id FROM reaction_sets WHERE name='Set 1'").fetchone()["id"]
    conn.execute(
        "INSERT INTO reactions (reaction_set_id, reaction, verified) VALUES (?, ?, ?)",
        (reaction_set_id, "e + Ar -> e + Ar", 1),
    )
    reaction_id = conn.execute("SELECT id FROM reactions WHERE reaction_set_id=?", (reaction_set_id,)).fetchone()["id"]
    conn.execute(
        """
        INSERT INTO reaction_audits (reaction_id, action, changes, verified_by)
        VALUES (?, ?, ?, ?)
        """,
        (reaction_id, "verify", "{\"verified\": true}", "reviewer"),
    )

    category_columns = {row["name"] for row in conn.execute("PRAGMA table_info(categories)").fetchall()}
    paper_category_columns = {row["name"] for row in conn.execute("PRAGMA table_info(paper_categories)").fetchall()}
    audit_columns = {row["name"] for row in conn.execute("PRAGMA table_info(reaction_audits)").fetchall()}
    unique_indexes = {
        index["name"]: [
            row["name"] for row in conn.execute(f"PRAGMA index_info({index['name']})").fetchall()
        ]
        for index in conn.execute("PRAGMA index_list(categories)").fetchall()
        if index["unique"]
    }
    paper_category_unique_indexes = {
        index["name"]: [
            row["name"] for row in conn.execute(f"PRAGMA index_info({index['name']})").fetchall()
        ]
        for index in conn.execute("PRAGMA index_list(paper_categories)").fetchall()
        if index["unique"]
    }
    audit_index = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_reaction_audits_reaction'"
    ).fetchone()

    assert {"name", "slug", "description", "parent_id"}.issubset(category_columns)
    assert {"paper_id", "category_id", "confidence", "method", "created_at"}.issubset(paper_category_columns)
    assert {"reaction_id", "action", "changes", "verified_by", "created_at"}.issubset(audit_columns)
    assert ["slug"] in unique_indexes.values()
    assert ["paper_id", "category_id"] in paper_category_unique_indexes.values()
    assert audit_index is not None


def test_migrations_create_missing_core_tables_for_partial_legacy_database():
    import sqlite3

    from app.db import ensure_migrations

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE journals (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            active INTEGER DEFAULT 1
        );
        INSERT INTO journals (name, active) VALUES ('Legacy Journal', 1);
        """
    )

    ensure_migrations(conn)

    tables = {
        row["name"]
        for row in conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type IN ('table', 'view') AND name IN (
                'papers', 'papers_fts', 'categories', 'paper_categories',
                'crawl_jobs', 'documents', 'sections', 'translations',
                'chunks', 'reaction_sets', 'reactions', 'reaction_audits'
            )
            """
        ).fetchall()
    }
    journal_count = conn.execute("SELECT COUNT(*) AS n FROM journals").fetchone()["n"]
    journal_columns = {row["name"] for row in conn.execute("PRAGMA table_info(journals)").fetchall()}
    legacy_journal = conn.execute("SELECT * FROM journals WHERE name='Legacy Journal'").fetchone()
    paper_columns = {row["name"] for row in conn.execute("PRAGMA table_info(papers)").fetchall()}
    indexes = {
        row["name"]
        for row in conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='index' AND name IN (
                'idx_papers_journal', 'idx_papers_year', 'idx_papers_oa',
                'idx_crawljobs_journal', 'idx_documents_paper', 'idx_sections_doc',
                'idx_translations_doc', 'idx_chunks_doc', 'idx_rsets_doc',
                'idx_reactions_set', 'idx_reaction_audits_reaction'
            )
            """
        ).fetchall()
    }

    assert journal_count == 1
    assert legacy_journal["year_from"] == 1990
    assert legacy_journal["active"] == 1
    assert {
        "publisher",
        "platform",
        "url",
        "issn_print",
        "issn_electronic",
        "keywords",
        "year_from",
        "year_to",
        "sci_zone",
        "impact_factor",
        "created_at",
        "updated_at",
    }.issubset(journal_columns)
    assert {
        "papers",
        "papers_fts",
        "categories",
        "paper_categories",
        "crawl_jobs",
        "documents",
        "sections",
        "translations",
        "chunks",
        "reaction_sets",
        "reactions",
        "reaction_audits",
    }.issubset(tables)
    assert {
        "doi",
        "title",
        "abstract",
        "authors",
        "journal_id",
        "journal_name",
        "published_date",
        "published_year",
        "landing_url",
        "oa_status",
        "oa_pdf_url",
        "source_api",
        "dedupe_key",
        "raw_metadata",
        "indexed_at",
        "updated_at",
    }.issubset(paper_columns)
    assert {
        "idx_papers_journal",
        "idx_papers_year",
        "idx_papers_oa",
        "idx_crawljobs_journal",
        "idx_documents_paper",
        "idx_sections_doc",
        "idx_translations_doc",
        "idx_chunks_doc",
        "idx_rsets_doc",
        "idx_reactions_set",
        "idx_reaction_audits_reaction",
    }.issubset(indexes)

    conn.execute(
        """
        INSERT INTO journals (name, publisher, issn_print, keywords, year_from)
        VALUES ('New Migrated Journal', 'Example', '1234-5678', '[]', 2000)
        """
    )
    migrated_names = [row["name"] for row in conn.execute("SELECT name FROM journals ORDER BY id").fetchall()]
    assert migrated_names == ["Legacy Journal", "New Migrated Journal"]


def test_scheduler_creates_jobs_without_running_network(tmp_path):
    make_client(tmp_path)

    from app.scheduler import create_scheduler, trigger_scheduled_crawl

    scheduler = create_scheduler()
    job_ids = sorted(job.id for job in scheduler.get_jobs())
    assert job_ids == ["crawl-daily", "crawl-monthly", "crawl-weekly"]
    jobs = trigger_scheduled_crawl("weekly", dispatch=False)
    assert len(jobs) == 6


def test_system_status_reports_scheduled_crawl_jobs(tmp_path):
    client = make_client(tmp_path)

    runtime = client.get("/api/v1/system/status").json()["runtime"]

    assert runtime["scheduler_jobs"] == [
        {"id": "crawl-daily", "period": "daily", "trigger": "cron", "schedule": "day=*, hour=2", "timezone": "UTC"},
        {
            "id": "crawl-weekly",
            "period": "weekly",
            "trigger": "cron",
            "schedule": "day_of_week=mon, hour=3",
            "timezone": "UTC",
        },
        {"id": "crawl-monthly", "period": "monthly", "trigger": "cron", "schedule": "day=1, hour=4", "timezone": "UTC"},
    ]


def test_scheduler_dispatches_created_jobs_to_crawl_runner(monkeypatch):
    from app import scheduler as scheduler_module

    jobs = [
        {"job_id": 11, "journal_id": 2, "date_from": "2026-01-01", "date_to": "2026-01-07"},
        {"job_id": 12, "journal_id": 3, "date_from": "2026-01-01", "date_to": "2026-01-07"},
    ]
    calls = []

    def fake_create_jobs(journal_ids, period, date_from, date_to):
        assert journal_ids is None
        assert period == "weekly"
        assert date_from is None
        assert date_to is None
        return jobs

    async def fake_run_crawl_job(job_id, journal_id, date_from, date_to):
        calls.append((job_id, journal_id, date_from, date_to))

    monkeypatch.setattr(scheduler_module, "create_jobs", fake_create_jobs)
    monkeypatch.setattr(scheduler_module, "run_crawl_job", fake_run_crawl_job, raising=False)

    assert scheduler_module.trigger_scheduled_crawl("weekly") == jobs
    assert calls == [
        (11, 2, "2026-01-01", "2026-01-07"),
        (12, 3, "2026-01-01", "2026-01-07"),
    ]


def test_app_lifespan_starts_scheduler_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("PAPER_LAB_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PAPER_LAB_PDF_DIR", str(tmp_path / "pdfs"))
    monkeypatch.setenv("PAPER_LAB_TEI_DIR", str(tmp_path / "tei"))
    monkeypatch.setenv("PAPER_LAB_TRANSLATION_DIR", str(tmp_path / "translations"))
    monkeypatch.setenv("PAPER_LAB_EXPORT_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("VECTOR_DB_PATH", str(tmp_path / "vector-index.json"))
    monkeypatch.setenv("PAPER_LAB_SCHEDULER_ENABLED", "true")

    from app.config import get_settings
    from app import main as main_module
    from fastapi.testclient import TestClient

    calls = []

    class FakeScheduler:
        def start(self):
            calls.append("start")

        def shutdown(self, wait=False):
            calls.append(("shutdown", wait))

    get_settings.cache_clear()
    monkeypatch.setattr(main_module, "create_scheduler", lambda: FakeScheduler(), raising=False)

    with TestClient(main_module.create_app()) as client:
        assert client.get("/health").status_code == 200

    assert calls == ["start", ("shutdown", False)]


def test_openalex_client_paginates_and_retries():
    import asyncio

    import httpx

    from app.clients.openalex import OpenAlexClient

    attempts = 0
    seen_cursors = []

    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(500, json={"error": "temporary"})

        seen_cursors.append(request.url.params.get("cursor"))
        if request.url.params.get("cursor") == "*":
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "doi": "https://doi.org/10.1/one",
                            "title": "One",
                            "publication_year": 2026,
                            "primary_location": {"landing_page_url": "https://example.test/one"},
                        }
                    ],
                    "meta": {"next_cursor": "next-page"},
                },
            )
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "doi": "10.1/two",
                        "title": "Two",
                        "publication_year": 2025,
                    }
                ],
                "meta": {},
            },
        )

    client = OpenAlexClient("lab@example.test", transport=httpx.MockTransport(handler))
    works = asyncio.run(client.works_by_issn("1234-5678", "2025-01-01", "2026-01-01"))
    assert [work["doi"] for work in works] == ["10.1/one", "10.1/two"]
    assert seen_cursors == ["*", "next-page"]
    assert attempts == 3


def test_openalex_client_honors_retry_after_without_real_sleep():
    import asyncio

    import httpx

    from app.clients.openalex import OpenAlexClient

    attempts = 0
    delays = []

    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "1.5"}, json={"error": "rate limited"})
        return httpx.Response(200, json={"results": [], "meta": {}})

    async def fake_sleep(delay):
        delays.append(delay)

    client = OpenAlexClient(
        "lab@example.test",
        transport=httpx.MockTransport(handler),
        max_retries=2,
        retry_backoff_seconds=0.25,
        sleep=fake_sleep,
    )
    works = asyncio.run(client.works_by_issn("1234-5678", "2025-01-01", "2026-01-01"))

    assert works == []
    assert attempts == 2
    assert delays == [1.5]


def test_openalex_client_reconstructs_abstract_inverted_index():
    from app.clients.openalex import OpenAlexClient

    work = OpenAlexClient().normalize(
        {
            "doi": "https://doi.org/10.1/inverted",
            "title": "Inverted abstract",
            "abstract_inverted_index": {
                "Argon": [0],
                "plasma": [1, 6],
                "chemistry": [2],
                "drives": [3],
                "oxygen": [4],
                "reaction": [5],
            },
            "publication_date": "2026-02-03",
            "publication_year": 2026,
        }
    )

    assert work["abstract"] == "Argon plasma chemistry drives oxygen reaction plasma"


def test_openalex_client_prefers_primary_landing_page_url():
    from app.clients.openalex import OpenAlexClient

    work = OpenAlexClient().normalize(
        {
            "id": "https://openalex.org/W123",
            "doi": "https://doi.org/10.1/landing",
            "title": "Landing page preference",
            "primary_location": {
                "landing_page_url": "https://publisher.example/article/10.1/landing",
                "source": {"display_name": "Publisher Journal"},
            },
        }
    )

    assert work["landing_url"] == "https://publisher.example/article/10.1/landing"


def test_crossref_client_paginates():
    import asyncio

    import httpx

    from app.clients.crossref import CrossrefClient

    seen_cursors = []

    def handler(request):
        cursor = request.url.params.get("cursor")
        seen_cursors.append(cursor)
        if cursor == "*":
            return httpx.Response(
                200,
                json={
                    "message": {
                        "items": [
                            {
                                "DOI": "10.2/one",
                                "title": ["First title"],
                                "published-print": {"date-parts": [[2024, 5, 1]]},
                            }
                        ],
                        "next-cursor": "next-crossref",
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "message": {
                    "items": [
                        {
                            "DOI": "10.2/two",
                            "title": ["Second title"],
                            "published-online": {"date-parts": [[2025]]},
                        }
                    ],
                    "next-cursor": cursor,
                }
            },
        )

    client = CrossrefClient("lab@example.test", transport=httpx.MockTransport(handler))
    works = asyncio.run(client.works_by_issn("1234-5678", "2024-01-01", "2026-01-01"))
    assert [work["doi"] for work in works] == ["10.2/one", "10.2/two"]
    assert works[0]["published_date"] == "2024-05-01"
    assert seen_cursors == ["*", "next-crossref"]


def test_crossref_client_strips_jats_tags_from_abstract():
    from app.clients.crossref import CrossrefClient

    work = CrossrefClient().normalize(
        {
            "DOI": "10.2/jats",
            "title": ["Tagged abstract"],
            "abstract": "<jats:p>Argon <jats:italic>plasma</jats:italic> chemistry &amp; kinetics.</jats:p>",
            "published-online": {"date-parts": [[2026, 4, 5]]},
        }
    )

    assert work["abstract"] == "Argon plasma chemistry & kinetics."


def test_crossref_client_uses_issued_date_when_published_dates_are_missing():
    from app.clients.crossref import CrossrefClient

    work = CrossrefClient().normalize(
        {
            "DOI": "10.2/issued",
            "title": ["Issued date only"],
            "issued": {"date-parts": [[2026, 6, 24]]},
        }
    )

    assert work["published_date"] == "2026-06-24"
    assert work["published_year"] == 2026


def test_unpaywall_client_honors_retry_after_without_real_sleep():
    import asyncio

    import httpx

    from app.clients.unpaywall import UnpaywallClient

    attempts = 0
    delays = []

    def handler(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "2"}, json={"error": "rate limited"})
        return httpx.Response(
            200,
            json={"oa_status": "green", "best_oa_location": {"url_for_pdf": "https://example.test/paper.pdf"}},
        )

    async def fake_sleep(delay):
        delays.append(delay)

    client = UnpaywallClient(
        "lab@example.test",
        transport=httpx.MockTransport(handler),
        max_retries=2,
        retry_backoff_seconds=0.25,
        sleep=fake_sleep,
    )
    result = asyncio.run(client.resolve("10.1/rate-limited"))

    assert result["oa_status"] == "green"
    assert result["oa_pdf_url"] == "https://example.test/paper.pdf"
    assert attempts == 2
    assert delays == [2.0]


def test_unpaywall_client_uses_best_location_url_when_it_is_pdf():
    import asyncio

    import httpx

    from app.clients.unpaywall import UnpaywallClient

    def handler(request):
        return httpx.Response(
            200,
            json={
                "oa_status": "green",
                "best_oa_location": {
                    "url_for_pdf": None,
                    "url": "https://repository.example.test/article.pdf?download=1",
                    "url_for_landing_page": "https://repository.example.test/article",
                },
            },
        )

    client = UnpaywallClient("lab@example.test", transport=httpx.MockTransport(handler))

    result = asyncio.run(client.resolve("10.1/pdf-in-best-url"))

    assert result["oa_status"] == "green"
    assert result["oa_pdf_url"] == "https://repository.example.test/article.pdf?download=1"


def test_resolve_oa_passes_unpaywall_retry_and_timeout_settings(tmp_path, monkeypatch):
    client = make_client(tmp_path)

    from app.config import get_settings
    from app.db import get_conn
    from app.routers import papers as papers_router

    get_settings.cache_clear()
    monkeypatch.setenv("UNPAYWALL_API_MAX_RETRIES", "6")
    monkeypatch.setenv("UNPAYWALL_API_RETRY_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("UNPAYWALL_API_REQUEST_INTERVAL_SECONDS", "0.4")
    monkeypatch.setenv("UNPAYWALL_API_TIMEOUT_SECONDS", "11")

    created = []

    class FakeUnpaywallClient:
        def __init__(self, email, **kwargs):
            created.append((email, kwargs))

        async def resolve(self, doi):
            return {"oa_status": "gold", "oa_pdf_url": "https://example.test/manual-oa.pdf"}

    monkeypatch.setattr(papers_router, "UnpaywallClient", FakeUnpaywallClient)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO papers (doi, title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, ?, '[]', 'fixture', '{}')
            """,
            ("10.7/manual-resolve", "Manual OA resolve", "argon plasma"),
        )
        paper_id = cursor.lastrowid

    response = client.post(f"/api/v1/papers/{paper_id}/resolve-oa")

    assert response.status_code == 200
    assert response.json()["oa_pdf_url"] == "https://example.test/manual-oa.pdf"
    assert created == [
        (
            None,
            {
                "max_retries": 6,
                "retry_backoff_seconds": 0.0,
                "request_interval_seconds": 0.4,
                "timeout": 11.0,
            },
        )
    ]


def test_resolve_oa_records_failure_without_server_error(tmp_path, monkeypatch):
    client = make_client(tmp_path)

    from app.db import get_conn
    from app.routers import papers as papers_router

    class FailingUnpaywallClient:
        def __init__(self, *args, **kwargs):
            pass

        async def resolve(self, doi):
            raise RuntimeError("Unpaywall temporary outage")

    monkeypatch.setattr(papers_router, "UnpaywallClient", FailingUnpaywallClient)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO papers (doi, title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, ?, '[]', 'fixture', ?)
            """,
            ("10.7/manual-resolve-failure", "Manual OA failure", "argon plasma", '{"source":"fixture"}'),
        )
        paper_id = cursor.lastrowid

    response = client.post(f"/api/v1/papers/{paper_id}/resolve-oa")

    assert response.status_code == 200
    payload = response.json()
    assert payload["oa_status"] == "unknown"
    assert payload["oa_pdf_url"] is None
    assert payload["raw_metadata"]["source"] == "fixture"
    assert payload["raw_metadata"]["oa_resolution_error"] == "Unpaywall temporary outage"


def test_resolve_oa_records_unpaywall_raw_metadata(tmp_path, monkeypatch):
    client = make_client(tmp_path)

    from app.db import get_conn
    from app.routers import papers as papers_router

    class RawUnpaywallClient:
        def __init__(self, *args, **kwargs):
            pass

        async def resolve(self, doi):
            return {
                "oa_status": "green",
                "oa_pdf_url": "https://repository.example.test/paper.pdf",
                "raw": {
                    "doi": doi,
                    "oa_status": "green",
                    "best_oa_location": {"url_for_pdf": "https://repository.example.test/paper.pdf"},
                },
            }

    monkeypatch.setattr(papers_router, "UnpaywallClient", RawUnpaywallClient)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO papers (doi, title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, ?, '[]', 'fixture', ?)
            """,
            ("10.7/manual-resolve-raw", "Manual OA raw", "argon plasma", '{"source":"fixture"}'),
        )
        paper_id = cursor.lastrowid

    response = client.post(f"/api/v1/papers/{paper_id}/resolve-oa")

    assert response.status_code == 200
    payload = response.json()
    assert payload["oa_status"] == "green"
    assert payload["oa_pdf_url"] == "https://repository.example.test/paper.pdf"
    assert payload["raw_metadata"]["source"] == "fixture"
    assert payload["raw_metadata"]["unpaywall"]["doi"] == "10.7/manual-resolve-raw"
    assert payload["raw_metadata"]["unpaywall"]["oa_status"] == "green"
    assert "oa_resolution_error" not in payload["raw_metadata"]


def test_resolve_oa_uses_and_stores_normalized_doi(tmp_path, monkeypatch):
    client = make_client(tmp_path)

    from app.db import get_conn
    from app.routers import papers as papers_router

    resolved_dois = []

    class RawUnpaywallClient:
        def __init__(self, *args, **kwargs):
            pass

        async def resolve(self, doi):
            resolved_dois.append(doi)
            return {
                "oa_status": "green",
                "oa_pdf_url": "https://repository.example.test/normalized.pdf",
                "raw": {"doi": doi, "oa_status": "green"},
            }

    monkeypatch.setattr(papers_router, "UnpaywallClient", RawUnpaywallClient)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO papers (doi, title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, ?, '[]', 'fixture', ?)
            """,
            ("https://doi.org/10.7/Manual.Resolve", "Manual OA normalized", "argon plasma", '{"source":"fixture"}'),
        )
        paper_id = cursor.lastrowid

    response = client.post(f"/api/v1/papers/{paper_id}/resolve-oa")

    assert response.status_code == 200
    payload = response.json()
    assert resolved_dois == ["10.7/manual.resolve"]
    assert payload["doi"] == "10.7/manual.resolve"
    assert payload["raw_metadata"]["unpaywall"]["doi"] == "10.7/manual.resolve"


def test_crawl_job_passes_api_retry_and_page_settings(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.config import get_settings
    from app.services import crawl as crawl_service

    get_settings.cache_clear()
    monkeypatch.setenv("ACADEMIC_API_MAX_PAGES", "4")
    monkeypatch.setenv("ACADEMIC_API_MAX_RETRIES", "5")
    monkeypatch.setenv("ACADEMIC_API_RETRY_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("ACADEMIC_API_REQUEST_INTERVAL_SECONDS", "0.3")
    monkeypatch.setenv("ACADEMIC_API_TIMEOUT_SECONDS", "7")

    created = []
    calls = []

    class FakeOpenAlexClient:
        def __init__(self, mailto, **kwargs):
            created.append(("openalex", mailto, kwargs))

        async def works_by_issn(self, issn, date_from, date_to, max_pages=None):
            calls.append(("openalex", issn, date_from, date_to, max_pages))
            return []

    class FakeCrossrefClient:
        def __init__(self, mailto, **kwargs):
            created.append(("crossref", mailto, kwargs))

        async def works_by_issn(self, issn, date_from, date_to, max_pages=None):
            calls.append(("crossref", issn, date_from, date_to, max_pages))
            return []

    class FakeUnpaywallClient:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(crawl_service, "OpenAlexClient", FakeOpenAlexClient)
    monkeypatch.setattr(crawl_service, "CrossrefClient", FakeCrossrefClient)
    monkeypatch.setattr(crawl_service, "UnpaywallClient", FakeUnpaywallClient)

    job = crawl_service.create_jobs([2], "manual", "2026-01-01", "2026-01-31")[0]
    import asyncio

    asyncio.run(crawl_service.run_crawl_job(job["job_id"], 2, "2026-01-01", "2026-01-31"))

    assert created == [
        (
            "openalex",
            None,
            {
                "max_retries": 5,
                "retry_backoff_seconds": 0.0,
                "request_interval_seconds": 0.3,
                "timeout": 7.0,
            },
        ),
        (
            "crossref",
            None,
            {
                "max_retries": 5,
                "retry_backoff_seconds": 0.0,
                "request_interval_seconds": 0.3,
                "timeout": 7.0,
            },
        ),
    ]
    assert calls == [
        ("openalex", "1361-6595", "2026-01-01", "2026-01-31", 4),
        ("crossref", "1361-6595", "2026-01-01", "2026-01-31", 4),
    ]


def test_crawl_job_falls_back_to_crossref_when_openalex_fails(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import crawl as crawl_service

    class FailingOpenAlexClient:
        def __init__(self, *args, **kwargs):
            pass

        async def works_by_issn(self, *args, **kwargs):
            raise RuntimeError("OpenAlex temporary outage")

    class FakeCrossrefClient:
        def __init__(self, *args, **kwargs):
            pass

        async def works_by_issn(self, *args, **kwargs):
            return [
                {
                    "doi": "10.4/crossref-fallback",
                    "title": "Crossref fallback plasma chemistry paper",
                    "abstract": "argon plasma chemistry",
                    "authors": [],
                    "published_date": "2026-01-03",
                    "published_year": 2026,
                    "landing_url": "https://example.test/crossref-fallback",
                    "source_api": "crossref",
                    "raw_metadata": {},
                }
            ]

    class FakeUnpaywallClient:
        def __init__(self, *args, **kwargs):
            pass

        async def resolve(self, doi):
            return {"oa_status": "unknown", "oa_pdf_url": None}

    monkeypatch.setattr(crawl_service, "OpenAlexClient", FailingOpenAlexClient)
    monkeypatch.setattr(crawl_service, "CrossrefClient", FakeCrossrefClient)
    monkeypatch.setattr(crawl_service, "UnpaywallClient", FakeUnpaywallClient)

    job = crawl_service.create_jobs([2], "manual", "2026-01-01", "2026-01-31")[0]
    import asyncio

    asyncio.run(crawl_service.run_crawl_job(job["job_id"], 2, "2026-01-01", "2026-01-31"))

    with get_conn() as conn:
        stored_job = conn.execute("SELECT * FROM crawl_jobs WHERE id=?", (job["job_id"],)).fetchone()
        paper = conn.execute("SELECT doi, source_api FROM papers WHERE doi=?", ("10.4/crossref-fallback",)).fetchone()

    assert stored_job["status"] == "success"
    assert stored_job["papers_found"] == 1
    assert stored_job["papers_new"] == 1
    assert "OpenAlex failed; used Crossref fallback" in stored_job["error"]
    assert paper["source_api"] == "crossref"


def test_crawl_job_records_diagnostic_when_openalex_empty_uses_crossref(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import crawl as crawl_service

    class EmptyOpenAlexClient:
        def __init__(self, *args, **kwargs):
            pass

        async def works_by_issn(self, *args, **kwargs):
            return []

    class FakeCrossrefClient:
        def __init__(self, *args, **kwargs):
            pass

        async def works_by_issn(self, *args, **kwargs):
            return [
                {
                    "doi": "10.4/crossref-empty-fallback",
                    "title": "Crossref empty fallback plasma chemistry paper",
                    "abstract": "argon plasma chemistry",
                    "authors": [],
                    "published_date": "2026-01-03",
                    "published_year": 2026,
                    "landing_url": "https://example.test/crossref-empty-fallback",
                    "source_api": "crossref",
                    "raw_metadata": {},
                }
            ]

    class FakeUnpaywallClient:
        def __init__(self, *args, **kwargs):
            pass

        async def resolve(self, doi):
            return {"oa_status": "unknown", "oa_pdf_url": None}

    monkeypatch.setattr(crawl_service, "OpenAlexClient", EmptyOpenAlexClient)
    monkeypatch.setattr(crawl_service, "CrossrefClient", FakeCrossrefClient)
    monkeypatch.setattr(crawl_service, "UnpaywallClient", FakeUnpaywallClient)

    job = crawl_service.create_jobs([2], "manual", "2026-01-01", "2026-01-31")[0]
    import asyncio

    asyncio.run(crawl_service.run_crawl_job(job["job_id"], 2, "2026-01-01", "2026-01-31"))

    with get_conn() as conn:
        stored_job = conn.execute("SELECT * FROM crawl_jobs WHERE id=?", (job["job_id"],)).fetchone()
        paper = conn.execute("SELECT doi, source_api FROM papers WHERE doi=?", ("10.4/crossref-empty-fallback",)).fetchone()

    assert stored_job["status"] == "success"
    assert stored_job["papers_found"] == 1
    assert stored_job["papers_new"] == 1
    assert "OpenAlex returned no works; used Crossref fallback" in stored_job["error"]
    assert paper["source_api"] == "crossref"


def test_crawl_job_passes_unpaywall_retry_and_timeout_settings(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.config import get_settings
    from app.services import crawl as crawl_service

    get_settings.cache_clear()
    monkeypatch.setenv("UNPAYWALL_API_MAX_RETRIES", "4")
    monkeypatch.setenv("UNPAYWALL_API_RETRY_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("UNPAYWALL_API_REQUEST_INTERVAL_SECONDS", "0.2")
    monkeypatch.setenv("UNPAYWALL_API_TIMEOUT_SECONDS", "9")

    created = []

    class FakeOpenAlexClient:
        def __init__(self, *args, **kwargs):
            pass

        async def works_by_issn(self, *args, **kwargs):
            return [
                {
                    "doi": "10.5/unpaywall-options",
                    "title": "Plasma chemistry OA options",
                    "abstract": "argon plasma chemistry",
                    "authors": [],
                    "published_date": "2026-02-01",
                    "published_year": 2026,
                    "landing_url": "https://example.test/oa-options",
                    "source_api": "openalex",
                    "raw_metadata": {},
                }
            ]

    class FakeUnpaywallClient:
        def __init__(self, email, **kwargs):
            created.append((email, kwargs))

        async def resolve(self, doi):
            return {"oa_status": "green", "oa_pdf_url": "https://example.test/oa.pdf"}

    monkeypatch.setattr(crawl_service, "OpenAlexClient", FakeOpenAlexClient)
    monkeypatch.setattr(crawl_service, "UnpaywallClient", FakeUnpaywallClient)

    job = crawl_service.create_jobs([2], "manual", "2026-02-01", "2026-02-28")[0]
    import asyncio

    asyncio.run(crawl_service.run_crawl_job(job["job_id"], 2, "2026-02-01", "2026-02-28"))

    assert created == [
        (
            None,
            {
                "max_retries": 4,
                "retry_backoff_seconds": 0.0,
                "request_interval_seconds": 0.2,
                "timeout": 9.0,
            },
        )
    ]


def test_crawl_job_records_unpaywall_failure_in_paper_metadata(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import crawl as crawl_service
    from app.utils import json_loads

    class FakeOpenAlexClient:
        def __init__(self, *args, **kwargs):
            pass

        async def works_by_issn(self, *args, **kwargs):
            return [
                {
                    "doi": "10.5/unpaywall-failure",
                    "title": "Plasma chemistry OA failure",
                    "abstract": "argon plasma chemistry",
                    "authors": [],
                    "published_date": "2026-02-01",
                    "published_year": 2026,
                    "landing_url": "https://example.test/oa-failure",
                    "source_api": "openalex",
                    "raw_metadata": {"source_id": "W-unpaywall-failure"},
                }
            ]

    class FailingUnpaywallClient:
        def __init__(self, *args, **kwargs):
            pass

        async def resolve(self, doi):
            raise RuntimeError("Unpaywall temporary outage")

    monkeypatch.setattr(crawl_service, "OpenAlexClient", FakeOpenAlexClient)
    monkeypatch.setattr(crawl_service, "UnpaywallClient", FailingUnpaywallClient)

    job = crawl_service.create_jobs([2], "manual", "2026-02-01", "2026-02-28")[0]
    import asyncio

    asyncio.run(crawl_service.run_crawl_job(job["job_id"], 2, "2026-02-01", "2026-02-28"))

    with get_conn() as conn:
        stored_job = conn.execute("SELECT * FROM crawl_jobs WHERE id=?", (job["job_id"],)).fetchone()
        paper = conn.execute(
            "SELECT oa_status, oa_pdf_url, raw_metadata FROM papers WHERE doi=?",
            ("10.5/unpaywall-failure",),
        ).fetchone()

    raw_metadata = json_loads(paper["raw_metadata"], {})
    assert stored_job["status"] == "success"
    assert paper["oa_status"] == "unknown"
    assert paper["oa_pdf_url"] is None
    assert raw_metadata["source_id"] == "W-unpaywall-failure"
    assert raw_metadata["oa_resolution_error"] == "Unpaywall temporary outage"


def test_crawl_job_records_found_filtered_and_new_counts(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import crawl as crawl_service

    class FakeOpenAlexClient:
        def __init__(self, *args, **kwargs):
            pass

        async def works_by_issn(self, *args, **kwargs):
            return [
                {
                    "doi": "10.3/match",
                    "title": "Plasma chemistry model",
                    "abstract": "argon oxygen plasma chemistry",
                    "authors": [],
                    "published_date": "2026-01-01",
                    "published_year": 2026,
                    "landing_url": "https://example.test/match",
                    "source_api": "openalex",
                    "raw_metadata": {},
                },
                {
                    "doi": "10.3/skip",
                    "title": "Unrelated optics paper",
                    "abstract": "thin film optics",
                    "authors": [],
                    "published_date": "2026-01-02",
                    "published_year": 2026,
                    "landing_url": "https://example.test/skip",
                    "source_api": "openalex",
                    "raw_metadata": {},
                },
            ]

    class FakeUnpaywallClient:
        def __init__(self, *args, **kwargs):
            pass

        async def resolve(self, doi):
            return {"oa_status": "gold", "oa_pdf_url": f"https://example.test/{doi}.pdf"}

    monkeypatch.setattr(crawl_service, "OpenAlexClient", FakeOpenAlexClient)
    monkeypatch.setattr(crawl_service, "UnpaywallClient", FakeUnpaywallClient)

    job_ids = crawl_service.create_jobs([2], "manual", "2026-01-01", "2026-01-31")
    import asyncio

    job_id = job_ids[0]["job_id"]
    asyncio.run(crawl_service.run_crawl_job(job_id, 2, "2026-01-01", "2026-01-31"))

    with get_conn() as conn:
        job = conn.execute("SELECT * FROM crawl_jobs WHERE id=?", (job_id,)).fetchone()
        papers = conn.execute("SELECT doi FROM papers ORDER BY doi").fetchall()

    assert job["status"] == "success"
    assert job["papers_found"] == 2
    assert job["papers_filtered"] == 1
    assert job["papers_new"] == 1
    assert [paper["doi"] for paper in papers] == ["10.3/match"]


def test_crawl_job_auto_classifies_accepted_papers(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import crawl as crawl_service

    class FakeOpenAlexClient:
        def __init__(self, *args, **kwargs):
            pass

        async def works_by_issn(self, *args, **kwargs):
            return [
                {
                    "doi": "10.3/auto-classified",
                    "title": "Plasma chemistry benchmark",
                    "abstract": "argon oxygen plasma chemistry",
                    "authors": [],
                    "published_date": "2026-01-01",
                    "published_year": 2026,
                    "landing_url": "https://example.test/auto-classified",
                    "source_api": "openalex",
                    "raw_metadata": {},
                }
            ]

    class FakeUnpaywallClient:
        def __init__(self, *args, **kwargs):
            pass

        async def resolve(self, doi):
            return {"oa_status": "gold", "oa_pdf_url": f"https://example.test/{doi}.pdf"}

    monkeypatch.setattr(crawl_service, "OpenAlexClient", FakeOpenAlexClient)
    monkeypatch.setattr(crawl_service, "UnpaywallClient", FakeUnpaywallClient)

    job_ids = crawl_service.create_jobs([2], "manual", "2026-01-01", "2026-01-31")
    import asyncio

    asyncio.run(crawl_service.run_crawl_job(job_ids[0]["job_id"], 2, "2026-01-01", "2026-01-31"))

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT c.slug, pc.method
            FROM papers p
            JOIN paper_categories pc ON pc.paper_id = p.id
            JOIN categories c ON c.id = pc.category_id
            WHERE p.doi = ?
            ORDER BY c.slug
            """,
            ("10.3/auto-classified",),
        ).fetchall()

    assert [(row["slug"], row["method"]) for row in rows] == [("chemistry", "auto")]


def test_crawl_job_resolves_oa_with_normalized_doi(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import crawl as crawl_service

    resolved_dois = []

    class FakeOpenAlexClient:
        def __init__(self, *args, **kwargs):
            pass

        async def works_by_issn(self, *args, **kwargs):
            return [
                {
                    "doi": "https://doi.org/10.3/Match.Case",
                    "title": "Plasma chemistry model",
                    "abstract": "argon oxygen plasma chemistry",
                    "authors": [],
                    "published_date": "2026-01-01",
                    "published_year": 2026,
                    "landing_url": "https://example.test/match",
                    "source_api": "openalex",
                    "raw_metadata": {},
                }
            ]

    class FakeUnpaywallClient:
        def __init__(self, *args, **kwargs):
            pass

        async def resolve(self, doi):
            resolved_dois.append(doi)
            return {"oa_status": "gold", "oa_pdf_url": f"https://example.test/{doi}.pdf"}

    monkeypatch.setattr(crawl_service, "OpenAlexClient", FakeOpenAlexClient)
    monkeypatch.setattr(crawl_service, "UnpaywallClient", FakeUnpaywallClient)

    job_ids = crawl_service.create_jobs([2], "manual", "2026-01-01", "2026-01-31")
    import asyncio

    job_id = job_ids[0]["job_id"]
    asyncio.run(crawl_service.run_crawl_job(job_id, 2, "2026-01-01", "2026-01-31"))

    with get_conn() as conn:
        paper = conn.execute("SELECT doi, oa_pdf_url FROM papers WHERE title=?", ("Plasma chemistry model",)).fetchone()

    assert resolved_dois == ["10.3/match.case"]
    assert paper["doi"] == "10.3/match.case"
    assert paper["oa_pdf_url"] == "https://example.test/10.3/match.case.pdf"


def test_crawl_run_rejects_invalid_period_and_reversed_dates(tmp_path):
    client = make_client(tmp_path)

    invalid_period = client.post(
        "/api/v1/crawl/run",
        json={"journal_ids": [2], "period": "hourly", "date_from": "2026-01-01", "date_to": "2026-01-31"},
    )
    reversed_dates = client.post(
        "/api/v1/crawl/run",
        json={"journal_ids": [2], "period": "manual", "date_from": "2026-02-01", "date_to": "2026-01-31"},
    )

    assert invalid_period.status_code == 422
    assert invalid_period.json()["error"]["code"] == "validation_error"
    assert reversed_dates.status_code == 422
    assert reversed_dates.json()["error"]["code"] == "validation_error"


def test_crawl_run_response_includes_created_job_context(tmp_path, monkeypatch):
    client = make_client(tmp_path)

    from app.routers import crawl as crawl_router

    def fake_create_jobs(journal_ids, period, date_from, date_to):
        assert journal_ids == [2]
        assert period == "weekly"
        assert date_from == "2026-06-01"
        assert date_to == "2026-06-07"
        return [
            {
                "job_id": 42,
                "journal_id": 2,
                "period": period,
                "date_from": date_from,
                "date_to": date_to,
            }
        ]

    async def fake_run_crawl_job(job_id, journal_id, date_from, date_to):
        return None

    monkeypatch.setattr(crawl_router, "create_jobs", fake_create_jobs)
    monkeypatch.setattr(crawl_router, "run_crawl_job", fake_run_crawl_job)

    response = client.post(
        "/api/v1/crawl/run",
        json={"journal_ids": [2], "period": "weekly", "date_from": "2026-06-01", "date_to": "2026-06-07"},
    )

    assert response.status_code == 202
    assert response.json() == {
        "jobs": [
            {
                "job_id": 42,
                "journal_id": 2,
                "period": "weekly",
                "date_from": "2026-06-01",
                "date_to": "2026-06-07",
                "status": "pending",
            }
        ]
    }


def test_crawl_run_rejects_empty_and_non_positive_journal_ids(tmp_path):
    client = make_client(tmp_path)

    empty_journal_ids = client.post(
        "/api/v1/crawl/run",
        json={"journal_ids": [], "period": "manual", "date_from": "2026-01-01", "date_to": "2026-01-31"},
    )
    non_positive_journal_ids = client.post(
        "/api/v1/crawl/run",
        json={"journal_ids": [2, 0, -1], "period": "manual", "date_from": "2026-01-01", "date_to": "2026-01-31"},
    )

    assert empty_journal_ids.status_code == 422
    assert empty_journal_ids.json()["error"]["code"] == "validation_error"
    assert non_positive_journal_ids.status_code == 422
    assert non_positive_journal_ids.json()["error"]["code"] == "validation_error"


def test_crawl_run_rejects_partially_unknown_journal_ids_without_creating_jobs(tmp_path, monkeypatch):
    client = make_client(tmp_path)

    from app.db import get_conn
    from app.routers import crawl as crawl_router

    async def fake_run_crawl_job(job_id, journal_id, date_from, date_to):
        return None

    monkeypatch.setattr(crawl_router, "run_crawl_job", fake_run_crawl_job)

    response = client.post(
        "/api/v1/crawl/run",
        json={"journal_ids": [2, 999], "period": "manual", "date_from": "2026-01-01", "date_to": "2026-01-31"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "journal_not_found"
    with get_conn() as conn:
        jobs = conn.execute("SELECT * FROM crawl_jobs").fetchall()
    assert jobs == []


def test_keyword_matching_supports_or_and_and_modes():
    from app.services.crawl import matches_keywords

    work = {"title": "Argon plasma model", "abstract": "oxygen chemistry benchmark"}

    assert matches_keywords(work, ["argon", "xenon"])
    assert matches_keywords(work, {"mode": "or", "terms": ["xenon", "oxygen"]})
    assert matches_keywords(work, {"mode": "and", "terms": ["argon", "chemistry"]})
    assert not matches_keywords(work, {"mode": "and", "terms": ["argon", "xenon"]})


def test_upsert_paper_deduplicates_no_doi_by_conservative_key(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn
    from app.services.crawl import upsert_paper

    journal = {"id": 2, "name": "Plasma Sources Science and Technology"}
    work = {
        "doi": None,
        "title": "No DOI plasma chemistry paper",
        "abstract": "argon oxygen chemistry",
        "authors": [],
        "published_date": "2026-02-01",
        "published_year": 2026,
        "landing_url": "https://example.test/no-doi",
        "source_api": "openalex",
        "raw_metadata": {"id": "W123"},
    }

    with get_conn() as conn:
        assert upsert_paper(conn, journal, work, {"oa_status": "unknown"}) is True
        updated = dict(work)
        updated["abstract"] = "updated abstract"
        assert upsert_paper(conn, journal, updated, {"oa_status": "unknown"}) is False
        papers = conn.execute("SELECT id, title, abstract, dedupe_key FROM papers").fetchall()

    assert len(papers) == 1
    assert papers[0]["abstract"] == "updated abstract"
    assert papers[0]["dedupe_key"].startswith("no-doi:")

    listed = client.get("/api/v1/papers", params={"q": "updated", "page_size": 1}).json()["items"][0]
    detail = client.get(f"/api/v1/papers/{papers[0]['id']}").json()
    for payload in [listed, detail]:
        assert payload["source_api"] == "openalex"
        assert payload["dedupe_key"] == papers[0]["dedupe_key"]
        assert payload["has_doi"] is False
        assert payload["dedupe_strategy"] == "no_doi_fingerprint"


def test_upsert_paper_normalizes_malformed_scalar_fields(tmp_path):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services.crawl import upsert_paper
    from app.utils import json_loads

    journal = {"id": 2, "name": "Plasma Sources Science and Technology"}
    work = {
        "doi": None,
        "title": ["bad title"],
        "abstract": {"value": "bad abstract"},
        "authors": "not-authors",
        "journal_name": {"value": "bad journal"},
        "published_date": ["2026-02-01"],
        "published_year": {"value": 2026},
        "landing_url": {"value": "bad url"},
        "source_api": {"value": "bad source"},
        "raw_metadata": ["not-object"],
    }

    with get_conn() as conn:
        assert (
            upsert_paper(
                conn,
                journal,
                work,
                {"oa_status": "unknown", "oa_pdf_url": ["bad"]},
            )
            is True
        )
        row = conn.execute(
            """
            SELECT title, abstract, authors, journal_name, published_date,
                   published_year, landing_url, source_api, raw_metadata, oa_pdf_url
            FROM papers
            WHERE title = ?
            """,
            ("Untitled",),
        ).fetchone()

    assert row is not None
    assert row["abstract"] == ""
    assert json_loads(row["authors"], None) == []
    assert row["journal_name"] == "Plasma Sources Science and Technology"
    assert row["published_date"] is None
    assert row["published_year"] is None
    assert row["landing_url"] is None
    assert row["source_api"] is None
    assert json_loads(row["raw_metadata"], None) == {}
    assert row["oa_pdf_url"] is None


def test_document_rag_chemistry_export_gate(tmp_path):
    client = make_client(tmp_path)
    content = pdf_bytes(b"This section describes plasma chemistry. e + Ar -> e + e + Ar+ . The rate is $k_1$ .")
    response = client.post(
        "/api/v1/documents",
        files={"file": ("sample.pdf", content, "application/pdf")},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    sections = client.get(f"/api/v1/documents/{document_id}/sections").json()["items"]
    assert sections

    translate_response = client.post(f"/api/v1/documents/{document_id}/translate", json={"target_lang": "zh"})
    assert translate_response.status_code == 202
    translate_payload = translate_response.json()
    assert translate_payload["status"] == "pending"
    assert translate_payload["document_id"] == document_id
    assert translate_payload["target_lang"] == "zh"
    assert isinstance(translate_payload["job_id"], int)
    translation = client.get(f"/api/v1/documents/{document_id}/translation").json()
    assert translation["status"] == "done"
    assert Path(translation["output_path"]).exists()

    assert client.post(f"/api/v1/documents/{document_id}/index").status_code == 202
    rag = client.post(
        "/api/v1/rag/query",
        json={"question": "plasma chemistry Ar", "document_ids": [document_id], "top_k": 3},
    ).json()
    assert rag["sources"]

    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_sets = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"]
    reaction_set_id = reaction_sets[0]["id"]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set_id}").json()
    assert detail["reactions"]
    reaction_id = detail["reactions"][0]["id"]

    blocked = client.post(f"/api/v1/reaction-sets/{reaction_set_id}/export")
    assert blocked.status_code == 409

    verified = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={"verified": True, "rate_value": "original k_1", "verified_by": "tester"},
    ).json()
    assert verified["status"] == "verified"
    exported = client.post(f"/api/v1/reaction-sets/{reaction_set_id}/export?format=json").json()
    assert Path(exported["output_path"]).exists()
    assert exported["reaction_count"] == 1
    assert exported["audit_entry_count"] == 1


def test_system_status_can_check_grobid_health(tmp_path, monkeypatch):
    client = make_client(tmp_path)

    from app.routers import system as system_router

    async def fake_health_detail(self):
        return {"available": False, "url": self.base_url, "error": "connection refused"}

    monkeypatch.setattr(system_router.GrobidClient, "health_detail", fake_health_detail)

    status = client.get("/api/v1/system/status?check_external=true").json()
    assert status["external_capabilities"]["grobid"]["url"] == "http://127.0.0.1:8070"
    assert status["external_capabilities"]["grobid"]["available"] is False
    assert status["external_capabilities"]["grobid"]["status_code"] is None
    assert status["external_capabilities"]["grobid"]["error"] == "connection refused"


def test_system_status_reports_missing_optional_config_without_blocking(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENALEX_MAILTO", "")
    monkeypatch.setenv("UNPAYWALL_EMAIL", "")
    monkeypatch.setenv("LLM_API_KEY", "")

    client = make_client(tmp_path)

    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    status = response.json()
    warnings = status["config_warnings"]
    codes = {warning["code"] for warning in warnings}
    assert "missing_openalex_mailto" in codes
    assert "missing_unpaywall_email" in codes
    assert "missing_llm_api_key" in codes
    assert all(warning["message"] for warning in warnings)
    assert all(warning["capability"] for warning in warnings)


def test_system_status_reports_corrupt_vector_store_health(tmp_path):
    client = make_client(tmp_path)
    (tmp_path / "vector-index.json").write_text("{not valid json", encoding="utf-8")

    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    vector_db = response.json()["storage_health"]["vector_db"]
    assert vector_db["path"] == str(tmp_path / "vector-index.json")
    assert vector_db["exists"] is True
    assert vector_db["readable"] is True
    assert vector_db["valid_json"] is False
    assert "Expecting property name enclosed in double quotes" in vector_db["error"]


def test_system_status_reports_vector_db_backend(tmp_path):
    client = make_client(tmp_path)

    status = client.get("/api/v1/system/status").json()

    assert status["external_capabilities"]["vector_db_backend"] == "local-json"


def test_parse_document_records_grobid_fallback_reason(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("sample.pdf", pdf_bytes(b"local plasma text"), "application/pdf")},
    )
    document_id = response.json()["id"]

    from app.services import documents as document_service

    async def fake_health_detail(self):
        return {
            "available": False,
            "url": "http://grobid.test",
            "status_code": None,
            "error": "connection refused",
        }

    monkeypatch.setattr(document_service.GrobidClient, "health_detail", fake_health_detail)

    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    document = client.get(f"/api/v1/documents/{document_id}").json()
    assert document["parse_status"] == "parsed"
    assert "GROBID is unavailable" in document["parse_error"]
    assert "connection refused" in document["parse_error"]


def test_parse_document_fallback_writes_valid_tei_xml(tmp_path, monkeypatch):
    import xml.etree.ElementTree as ET

    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("xml-fallback.pdf", pdf_bytes(b"Ar & O2 <plasma> chemistry"), "application/pdf")},
    )
    document_id = response.json()["id"]

    from app.services import documents as document_service

    async def fake_health_detail(self):
        return {
            "available": False,
            "url": "http://grobid.test",
            "status_code": None,
            "error": "connection refused",
        }

    monkeypatch.setattr(document_service.GrobidClient, "health_detail", fake_health_detail)

    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    document = client.get(f"/api/v1/documents/{document_id}").json()
    tei_text = Path(document["tei_path"]).read_text(encoding="utf-8")

    ET.fromstring(tei_text)
    assert "Ar &amp; O2 &lt;plasma&gt; chemistry" in tei_text


def test_parse_document_falls_back_when_grobid_returns_only_references(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("reference-only.pdf", pdf_bytes(b"local plasma body text"), "application/pdf")},
    )
    document_id = response.json()["id"]

    from app.db import get_conn
    from app.services import documents as document_service

    async def fake_health_detail(self):
        return {
            "available": True,
            "url": "http://grobid.test",
            "status_code": 200,
            "error": None,
        }

    async def fake_process_fulltext(self, file_path):
        return """
        <TEI xmlns="http://www.tei-c.org/ns/1.0">
          <text>
            <back>
              <listBibl>
                <bibl>Reference-only extraction.</bibl>
              </listBibl>
            </back>
          </text>
        </TEI>
        """

    monkeypatch.setattr(document_service.GrobidClient, "health_detail", fake_health_detail)
    monkeypatch.setattr(document_service.GrobidClient, "process_fulltext", fake_process_fulltext)

    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    document = client.get(f"/api/v1/documents/{document_id}").json()

    assert document["parse_status"] == "parsed"
    assert "GROBID returned no body sections" in document["parse_error"]
    with get_conn() as conn:
        sections = conn.execute(
            "SELECT title, content, section_type FROM sections WHERE document_id=? ORDER BY seq",
            (document_id,),
        ).fetchall()
    assert [dict(section) for section in sections] == [
        {
            "title": "Local extracted text",
            "content": "local plasma body text",
            "section_type": "body",
        }
    ]


def test_parse_document_records_failed_status_when_artifact_cleanup_fails(tmp_path, monkeypatch):
    import asyncio

    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("cleanup-fail.pdf", pdf_bytes(b"local plasma cleanup text"), "application/pdf")},
    )
    document_id = response.json()["id"]

    from app.db import get_conn
    from app.services import documents as document_service

    async def fake_health_detail(self):
        return {
            "available": False,
            "url": "http://grobid.test",
            "status_code": None,
            "error": "connection refused",
        }

    class FailingVectorStore:
        def __init__(self, path):
            self.path = path

        def delete_document(self, document_id):
            raise RuntimeError("vector cleanup failed")

    with get_conn() as conn:
        section_id = conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Stale', 'old parse section', 'body')
            """,
            (document_id,),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO chunks (document_id, section_id, seq, text, token_count, vector_id, embedded)
            VALUES (?, ?, 1, 'old parse chunk', 3, 'stale-vector-id', 1)
            """,
            (document_id, section_id),
        )
        conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status, output_path)
            VALUES (?, 'en', 'zh', 'done', ?)
            """,
            (document_id, str(tmp_path / "translations" / "stale.md")),
        )
        conn.execute(
            """
            INSERT INTO reaction_sets (document_id, name, source_note, status)
            VALUES (?, 'Stale reaction set', 'Old extraction', 'pending')
            """,
            (document_id,),
        )
        conn.execute(
            """
            UPDATE documents
            SET index_status='indexed',
                index_error='old index error',
                chemistry_status='extracted',
                chemistry_error='old chemistry error'
            WHERE id=?
            """,
            (document_id,),
        )

    monkeypatch.setattr(document_service.GrobidClient, "health_detail", fake_health_detail)
    monkeypatch.setattr(document_service, "JsonVectorStore", FailingVectorStore)

    result = asyncio.run(document_service.parse_document(document_id))

    assert result["parse_status"] == "failed"
    assert "vector cleanup failed" in result["parse_error"]
    with get_conn() as conn:
        document = conn.execute(
            """
            SELECT parse_status, parse_error, index_status, index_error, chemistry_status, chemistry_error
            FROM documents WHERE id=?
            """,
            (document_id,),
        ).fetchone()
        counts = {
            table: conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE document_id=?", (document_id,)).fetchone()["n"]
            for table in ["sections", "chunks", "translations", "reaction_sets"]
        }
    assert document["parse_status"] == "failed"
    assert "vector cleanup failed" in document["parse_error"]
    assert document["index_status"] == "not_indexed"
    assert document["index_error"] is None
    assert document["chemistry_status"] == "not_extracted"
    assert document["chemistry_error"] is None
    assert counts == {"sections": 0, "chunks": 0, "translations": 0, "reaction_sets": 0}


def test_parse_document_fallback_failure_clears_stale_artifacts(tmp_path, monkeypatch):
    import asyncio
    import json

    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("fallback-read-fail.pdf", pdf_bytes(b"stale local text"), "application/pdf")},
    )
    document_id = response.json()["id"]

    from app.db import get_conn
    from app.services import documents as document_service
    from app.services.rag import JsonVectorStore, local_hash_embedding

    async def fake_health_detail(self):
        return {
            "available": False,
            "url": "http://grobid.test",
            "status_code": None,
            "error": "connection refused",
        }

    def failing_read_document_text(file_path):
        raise RuntimeError("local text read failed")

    with get_conn() as conn:
        section_id = conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Stale', 'metastable stale evidence', 'body')
            """,
            (document_id,),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO chunks (document_id, section_id, seq, text, token_count, vector_id, embedded)
            VALUES (?, ?, 1, 'metastable stale evidence', 3, 'stale-vector-id', 1)
            """,
            (document_id, section_id),
        )
        conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status, output_path)
            VALUES (?, 'en', 'zh', 'done', ?)
            """,
            (document_id, str(tmp_path / "translations" / "stale.md")),
        )
        conn.execute(
            """
            INSERT INTO reaction_sets (document_id, name, source_note, status)
            VALUES (?, 'Stale reaction set', 'Old extraction', 'pending')
            """,
            (document_id,),
        )
        conn.execute(
            """
            UPDATE documents
            SET index_status='indexed',
                index_error='old index error',
                chemistry_status='extracted',
                chemistry_error='old chemistry error'
            WHERE id=?
            """,
            (document_id,),
        )

    JsonVectorStore(tmp_path / "vector-index.json").upsert_many(
        {
            "stale-vector-id": {
                "chunk_id": 1,
                "document_id": document_id,
                "section_id": section_id,
                "text": "metastable stale evidence",
                "embedding": local_hash_embedding("metastable stale evidence"),
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
                "dimensions": 64,
            }
        }
    )
    monkeypatch.setattr(document_service.GrobidClient, "health_detail", fake_health_detail)
    monkeypatch.setattr(document_service, "read_document_text", failing_read_document_text)

    result = asyncio.run(document_service.parse_document(document_id))

    assert result["parse_status"] == "failed"
    assert "Local text fallback failed: local text read failed" in result["parse_error"]
    with get_conn() as conn:
        document = conn.execute(
            """
            SELECT index_status, index_error, chemistry_status, chemistry_error
            FROM documents WHERE id=?
            """,
            (document_id,),
        ).fetchone()
        counts = {
            table: conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE document_id=?", (document_id,)).fetchone()["n"]
            for table in ["sections", "chunks", "translations", "reaction_sets"]
        }
    assert document["index_status"] == "not_indexed"
    assert document["index_error"] is None
    assert document["chemistry_status"] == "not_extracted"
    assert document["chemistry_error"] is None
    assert counts == {"sections": 0, "chunks": 0, "translations": 0, "reaction_sets": 0}
    vector_index = json.loads((tmp_path / "vector-index.json").read_text(encoding="utf-8"))
    assert all(record["document_id"] != document_id for record in vector_index.values())


def test_sections_from_tei_extracts_structured_sections():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <front>
          <abstract><p>Abstract plasma chemistry summary.</p></abstract>
        </front>
        <body>
          <div><head>Model</head><p>Body model content.</p></div>
          <figure><head>Figure 1</head><figDesc>Discharge geometry caption.</figDesc></figure>
          <table><head>Table 1</head><row><cell>Reaction</cell><cell>Rate</cell></row></table>
        </body>
        <back>
          <listBibl>
            <biblStruct><analytic><title>Reference paper</title></analytic></biblStruct>
          </listBibl>
        </back>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)
    assert [section["section_type"] for section in sections] == [
        "abstract",
        "body",
        "figure_caption",
        "table",
        "reference",
    ]
    assert sections[0]["title"] == "Abstract"
    assert "Body model content" in sections[1]["content"]
    assert "Discharge geometry caption" in sections[2]["content"]
    assert "Reaction Rate" in sections[3]["content"]
    assert "Reference paper" in sections[4]["content"]


def test_sections_from_tei_abstract_omits_head_from_content():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <front>
          <abstract>
            <head>Abstract</head>
            <p>Plasma chemistry summary.</p>
          </abstract>
        </front>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Abstract",
            "content": "Plasma chemistry summary.",
            "section_type": "abstract",
        }
    ]


def test_sections_from_tei_handles_tei_without_namespace():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI>
      <text>
        <front>
          <abstract><p>Abstract plasma chemistry summary.</p></abstract>
        </front>
        <body>
          <div><head>Introduction</head><p>Low temperature plasma body text.</p></div>
          <figure><head>Figure 1</head><figDesc>Discharge geometry caption.</figDesc></figure>
          <table><head>Table 1</head><row><cell>Reaction</cell><cell>Rate</cell></row></table>
        </body>
        <back>
          <listBibl>
            <biblStruct><analytic><title>Reference paper</title></analytic></biblStruct>
          </listBibl>
        </back>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert [section["section_type"] for section in sections] == [
        "abstract",
        "body",
        "figure_caption",
        "table",
        "reference",
    ]
    assert sections[1]["title"] == "Introduction"
    assert "Reaction Rate" in sections[3]["content"]
    assert "Reference paper" in sections[4]["content"]


def test_sections_from_tei_does_not_duplicate_nested_div_paragraphs():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <div>
            <head>Methods</head>
            <p>Parent method overview.</p>
            <div>
              <head>Plasma conditions</head>
              <p>Nested discharge pressure details.</p>
            </div>
          </div>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert [section["title"] for section in sections] == ["Methods", "Plasma conditions"]
    assert sections[0]["content"] == "Parent method overview."
    assert sections[1]["content"] == "Nested discharge pressure details."


def test_sections_from_tei_body_includes_direct_list_items():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <div>
            <head>Operating conditions</head>
            <p>Base discharge setup.</p>
            <list>
              <item>Pressure 10 Pa.</item>
              <item>Power 100 W.</item>
            </list>
          </div>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Operating conditions",
            "content": "Base discharge setup. Pressure 10 Pa. Power 100 W.",
            "section_type": "body",
        }
    ]


def test_sections_from_tei_preserves_body_table_document_order():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <div><head>Before table</head><p>Initial model description.</p></div>
          <table><head>Table 2</head><row><cell>Reaction</cell><cell>Rate</cell></row></table>
          <div><head>After table</head><p>Post-table discussion.</p></div>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert [(section["section_type"], section["title"]) for section in sections] == [
        ("body", "Before table"),
        ("table", "Table 2"),
        ("body", "After table"),
    ]


def test_sections_from_tei_preserves_div_table_document_order():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <div>
            <head>Experiment</head>
            <p>Before the table.</p>
            <table><head>Table 3</head><row><cell>Species</cell><cell>Density</cell></row></table>
            <p>After the table.</p>
          </div>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert [(section["section_type"], section["title"], section["content"]) for section in sections] == [
        ("body", "Experiment", "Before the table."),
        ("table", "Table 3", "Species Density"),
        ("body", "Experiment", "After the table."),
    ]


def test_sections_from_tei_uses_sequential_titles_for_split_untitled_div():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <div>
            <p>Before the table.</p>
            <table><head>Table 3</head><row><cell>Species</cell><cell>Density</cell></row></table>
            <p>After the table.</p>
          </div>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert [(section["section_type"], section["title"]) for section in sections] == [
        ("body", "Section 1"),
        ("table", "Table 3"),
        ("body", "Section 3"),
    ]


def test_sections_from_tei_extracts_direct_body_paragraphs():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <p>Standalone body paragraph before sections.</p>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Section 1",
            "content": "Standalone body paragraph before sections.",
            "section_type": "body",
        }
    ]


def test_sections_from_tei_uses_direct_body_head_for_following_paragraph():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <head>Results overview</head>
          <p>Standalone results paragraph.</p>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Results overview",
            "content": "Standalone results paragraph.",
            "section_type": "body",
        }
    ]


def test_sections_from_tei_groups_direct_body_paragraphs_under_head():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <head>Results overview</head>
          <p>First standalone paragraph.</p>
          <p>Second standalone paragraph.</p>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Results overview",
            "content": "First standalone paragraph. Second standalone paragraph.",
            "section_type": "body",
        }
    ]


def test_sections_from_tei_extracts_direct_body_list_items():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <list>
            <item>Metastable density rises.</item>
            <item>Ion flux remains stable.</item>
          </list>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Section 1",
            "content": "Metastable density rises. Ion flux remains stable.",
            "section_type": "body",
        }
    ]


def test_sections_from_tei_figure_fallback_omits_title_from_caption():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <figure>
            <head>Figure 2</head>
            <p>Measured ion density profile.</p>
          </figure>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Figure 2",
            "content": "Measured ion density profile.",
            "section_type": "figure_caption",
        }
    ]


def test_sections_from_tei_figure_fallback_preserves_text_after_head():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <figure><head>Figure 5</head>Measured ion density profile.</figure>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Figure 5",
            "content": "Measured ion density profile.",
            "section_type": "figure_caption",
        }
    ]


def test_sections_from_tei_table_fallback_omits_title_from_content():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <table>
            <head>Table 3</head>
            <p>Reaction rate constants from the appendix.</p>
          </table>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Table 3",
            "content": "Reaction rate constants from the appendix.",
            "section_type": "table",
        }
    ]


def test_sections_from_tei_table_figure_fallback_omits_title_and_duplicate_caption():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <body>
          <figure type="table">
            <head>Table 4</head>
            <figDesc>Measured reaction rates.</figDesc>
            <p>e + Ar -> e + e + Ar+</p>
          </figure>
        </body>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Table 4",
            "content": "Measured reaction rates. e + Ar -> e + e + Ar+",
            "section_type": "table",
        }
    ]


def test_sections_from_tei_extracts_simple_bibl_references():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <back>
          <listBibl>
            <bibl>Smith 2026 Plasma Chemistry reference.</bibl>
          </listBibl>
        </back>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Reference 1",
            "content": "Smith 2026 Plasma Chemistry reference.",
            "section_type": "reference",
        }
    ]


def test_sections_from_tei_extracts_biblfull_references():
    from app.services.documents import sections_from_tei

    tei = """
    <TEI xmlns="http://www.tei-c.org/ns/1.0">
      <text>
        <back>
          <listBibl>
            <biblFull>
              <titleStmt><title>Argon plasma kinetics</title></titleStmt>
              <publicationStmt><date>2026</date></publicationStmt>
            </biblFull>
          </listBibl>
        </back>
      </text>
    </TEI>
    """

    sections = sections_from_tei(tei)

    assert sections == [
        {
            "seq": 1,
            "title": "Reference 1",
            "content": "Argon plasma kinetics 2026",
            "section_type": "reference",
        }
    ]


def test_translation_adapter_preserves_formula_masks():
    from app.services.translation import translate_text_preserving_formulas

    class FakeTranslator:
        def translate(self, text, target_lang):
            assert target_lang == "zh"
            assert "$k_1$" not in text
            assert "$$E=mc^2$$" not in text
            assert "<EQ_000>" in text
            assert "<EQ_001>" in text
            return f"译文: {text}"

    translated = translate_text_preserving_formulas(
        "The rate is $k_1$ and the energy is $$E=mc^2$$.",
        FakeTranslator(),
        "zh",
    )
    assert "译文:" in translated
    assert "$k_1$" in translated
    assert "$$E=mc^2$$" in translated
    assert "<EQ_" not in translated


def test_openai_translation_adapter_uses_compatible_chat_completions_payload():
    import json

    import httpx

    from app.services.translation import OpenAICompatibleTranslator

    requests = []

    def handler(request):
        requests.append(request)
        payload = json.loads(request.content)
        assert request.url == "http://llm.test/v1/chat/completions"
        assert payload["model"] == "translate-model"
        assert payload["temperature"] == 0
        assert "Preserve placeholders like <EQ_000> exactly" in payload["messages"][0]["content"]
        assert payload["messages"][1]["content"] == "Target language: zh\n\nThe rate is <EQ_000>."
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "速率为 <EQ_000>。"}}]},
        )

    translator = OpenAICompatibleTranslator(
        "test-key",
        "http://llm.test/v1",
        "translate-model",
        transport=httpx.MockTransport(handler),
    )

    result = translator.translate("The rate is <EQ_000>.", "zh")

    assert result == "速率为 <EQ_000>。"
    assert requests[0].headers["authorization"] == "Bearer test-key"


def test_openai_classifier_keeps_only_registered_taxonomy_slugs():
    import json

    import httpx

    from app.services.classification import OpenAICompatibleClassifier

    requests = []

    def handler(request):
        requests.append(request)
        payload = json.loads(request.content)
        assert payload["model"] == "classify-model"
        assert "chemistry" in payload["messages"][1]["content"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "categories": [
                                        {"slug": "chemistry", "confidence": 0.91},
                                        {"slug": "imagined-category", "confidence": 0.8},
                                    ]
                                }
                            )
                        }
                    }
                ]
            },
        )

    classifier = OpenAICompatibleClassifier(
        "test-key",
        "http://llm.test/v1",
        "classify-model",
        transport=httpx.MockTransport(handler),
    )

    result = classifier.classify(
        "argon oxygen plasma chemistry",
        [{"id": 2, "slug": "chemistry", "name": "等离子体化学", "description": "reaction pathways"}],
    )

    assert result == [{"category_id": 2, "slug": "chemistry", "confidence": 0.91, "method": "auto"}]
    assert requests[0].headers["authorization"] == "Bearer test-key"


def test_translate_document_preserves_table_and_reference_sections(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import translation as translation_service

    calls = []

    class RecordingTranslator:
        def translate(self, text, target_lang):
            calls.append((text, target_lang))
            return f"translated::{text}"

    monkeypatch.setattr(translation_service, "get_translator", lambda settings: RecordingTranslator())

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            (str(tmp_path / "translated.pdf"), "translate-section-types", "translated.pdf"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Body', 'Body plasma equation $k_1$', 'body')
            """,
            (document_id,),
        )
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 2, 'Reaction Table', 'Reaction Rate e + Ar -> Ar+', 'table')
            """,
            (document_id,),
        )
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 3, 'Reference 1', 'Smith 2026 Plasma Chemistry', 'reference')
            """,
            (document_id,),
        )

    result = translation_service.translate_document(document_id, "zh")

    output = Path(result["output_path"]).read_text(encoding="utf-8")
    assert result["status"] == "done"
    assert calls == [("Body plasma equation <EQ_000>", "zh")]
    assert "translated::Body plasma equation $k_1$" in output
    assert "Reaction Rate e + Ar -> Ar+" in output
    assert "> Section type `table` is preserved without machine translation." in output
    assert "translated::Reaction Rate" not in output
    assert "Smith 2026 Plasma Chemistry" in output
    assert "> Section type `reference` is preserved without machine translation." in output
    assert "translated::Smith" not in output


def test_translate_document_fails_when_sections_have_no_text(tmp_path):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import translation as translation_service

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            (str(tmp_path / "empty-translation.pdf"), "empty-translation", "empty-translation.pdf"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Empty', '   ', 'body')
            """,
            (document_id,),
        )

    result = translation_service.translate_document(document_id, "zh")

    assert result["status"] == "failed"
    assert result["output_path"] is None
    assert "document has no translatable section text" in result["error"]
    with get_conn() as conn:
        row = conn.execute(
            "SELECT status, output_path, error FROM translations WHERE document_id=? ORDER BY id DESC LIMIT 1",
            (document_id,),
        ).fetchone()
    assert row["status"] == "failed"
    assert row["output_path"] is None
    assert "document has no translatable section text" in row["error"]


def test_translate_document_fails_when_only_preserved_sections_have_text(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import translation as translation_service

    calls = []

    class RecordingTranslator:
        def translate(self, text, target_lang):
            calls.append((text, target_lang))
            return f"translated::{text}"

    monkeypatch.setattr(translation_service, "get_translator", lambda settings: RecordingTranslator())

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            (str(tmp_path / "preserved-only.pdf"), "preserved-only", "preserved-only.pdf"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Reaction Table', 'Reaction Rate e + Ar -> Ar+', 'table')
            """,
            (document_id,),
        )
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 2, 'Reference 1', 'Smith 2026 Plasma Chemistry', 'reference')
            """,
            (document_id,),
        )

    result = translation_service.translate_document(document_id, "zh")

    assert result["status"] == "failed"
    assert result["output_path"] is None
    assert "document has no translatable section text" in result["error"]
    assert calls == []


def test_translate_document_failure_clears_stale_output_path(tmp_path):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import translation as translation_service

    stale_output = tmp_path / "translations" / "stale.md"
    stale_output.parent.mkdir(parents=True, exist_ok=True)
    stale_output.write_text("old translation", encoding="utf-8")
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            (str(tmp_path / "retry-translation.pdf"), "retry-translation", "retry-translation.pdf"),
        )
        document_id = cursor.lastrowid
        translation_id = conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status, output_path)
            VALUES (?, 'en', 'zh', 'done', ?)
            """,
            (document_id, str(stale_output)),
        ).lastrowid

    result = translation_service.translate_document(document_id, "zh", translation_id)

    assert result["status"] == "failed"
    assert result["output_path"] is None
    assert "document has no parsed sections" in result["error"]
    with get_conn() as conn:
        row = conn.execute("SELECT status, output_path, error FROM translations WHERE id=?", (translation_id,)).fetchone()
    assert row["status"] == "failed"
    assert row["output_path"] is None
    assert "document has no parsed sections" in row["error"]


def test_rag_index_uses_local_vector_store(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("rag.pdf", pdf_bytes(b"Argon plasma chemistry and electron impact reactions."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/index").status_code == 202

    import json

    vector_index = json.loads((tmp_path / "vector-index.json").read_text(encoding="utf-8"))
    assert vector_index
    first_record = next(iter(vector_index.values()))
    assert first_record["embedding_model"] == "local-hash"
    assert first_record["vector_db_backend"] == "local-json"
    assert first_record["embedding"]
    assert first_record["dimensions"] == len(first_record["embedding"])

    rag = client.post(
        "/api/v1/rag/query",
        json={"question": "electron impact chemistry", "document_ids": [document_id], "top_k": 2},
    ).json()
    assert rag["sources"]
    assert rag["sources"][0]["score"] > 0
    assert rag["sources"][0]["vector_id"]
    assert isinstance(rag["sources"][0]["chunk_id"], int)
    assert "electron impact reactions" in rag["sources"][0]["source_excerpt"]


def test_rag_sources_include_linked_paper_identity(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO papers (
                doi, title, abstract, authors, journal_id, journal_name,
                published_date, published_year, landing_url, oa_status,
                oa_pdf_url, source_api, raw_metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "10.1/rag-source",
                "Traceable argon plasma paper",
                "electron impact chemistry",
                "[]",
                2,
                "Plasma Sources Science and Technology",
                "2026-01-01",
                2026,
                "https://example.test/rag-source",
                "green",
                "https://example.test/rag-source.pdf",
                "fixture",
                "{}",
            ),
        )
        paper_id = cursor.lastrowid

    response = client.post(
        "/api/v1/documents",
        data={"paper_id": str(paper_id)},
        files={"file": ("traceable.pdf", pdf_bytes(b"Argon plasma electron impact chemistry evidence."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/index").status_code == 202

    rag = client.post(
        "/api/v1/rag/query",
        json={"question": "electron impact chemistry", "document_ids": [document_id], "top_k": 2},
    ).json()

    assert rag["sources"]
    assert rag["sources"][0]["paper_id"] == paper_id
    assert rag["sources"][0]["paper_title"] == "Traceable argon plasma paper"
    assert "electron impact chemistry evidence" in rag["sources"][0]["source_excerpt"]
    assert f"paper_id={paper_id}" in rag["answer"]
    assert "Traceable argon plasma paper" in rag["answer"]


def test_rag_query_treats_local_hash_collision_as_insufficient_evidence(tmp_path):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services.rag import index_document, query

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            ("/tmp/hash-collision.txt", "hash-collision", "hash-collision.txt"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Argon evidence', 'argon plasma chemistry evidence', 'body')
            """,
            (document_id,),
        )

    assert index_document(document_id)["status"] == "indexed"

    result = query("av", [document_id], 3)

    assert result["sources"] == []
    assert "证据不足" in result["answer"]


def test_rag_query_ignores_orphan_vector_records_without_chunks(tmp_path):
    make_client(tmp_path)

    from app.services.rag import JsonVectorStore, local_hash_embedding, query

    vector_store = JsonVectorStore(tmp_path / "vector-index.json")
    vector_store.upsert_many(
        {
            "orphan-vector": {
                "chunk_id": 999,
                "document_id": 1,
                "section_id": 888,
                "text": "electron impact chemistry evidence",
                "embedding": local_hash_embedding("electron impact chemistry evidence"),
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
                "dimensions": 64,
            }
        }
    )

    result = query("electron impact chemistry", [1], 3)

    assert result["sources"] == []
    assert "证据不足" in result["answer"]


def test_rag_query_ignores_stale_vector_text_that_no_longer_matches_chunk(tmp_path):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services.rag import JsonVectorStore, local_hash_embedding, query

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            ("/tmp/stale-vector.txt", "stale-vector", "stale-vector.txt"),
        )
        document_id = cursor.lastrowid
        section_id = conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Current section', 'oxygen plasma current evidence', 'body')
            """,
            (document_id,),
        ).lastrowid
        chunk_id = conn.execute(
            """
            INSERT INTO chunks (document_id, section_id, seq, text, token_count, vector_id, embedded)
            VALUES (?, ?, 1, 'oxygen plasma current evidence', 4, 'stale-vector-id', 1)
            """,
            (document_id, section_id),
        ).lastrowid

    JsonVectorStore(tmp_path / "vector-index.json").upsert_many(
        {
            "stale-vector-id": {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "section_id": section_id,
                "text": "metastable stale evidence",
                "embedding": local_hash_embedding("metastable stale evidence"),
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
                "dimensions": 64,
            }
        }
    )

    result = query("metastable", [document_id], 3)

    assert result["sources"] == []
    assert "证据不足" in result["answer"]


def test_rag_query_ignores_unembedded_chunks(tmp_path):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services.rag import query

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status, index_status)
            VALUES (?, ?, ?, 'parsed', 'indexing')
            """,
            ("/tmp/unembedded-rag.txt", "unembedded-rag", "unembedded-rag.txt"),
        )
        document_id = cursor.lastrowid
        section_id = conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Unfinished evidence', 'argon plasma unfinished evidence', 'body')
            """,
            (document_id,),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO chunks (document_id, section_id, seq, text, token_count, vector_id, embedded)
            VALUES (?, ?, 1, 'argon plasma unfinished evidence', 4, NULL, 0)
            """,
            (document_id, section_id),
        )

    result = query("argon plasma", [document_id], 3)

    assert result["sources"] == []
    assert "证据不足" in result["answer"]


def test_rag_reindex_replaces_stale_vectors_for_document(tmp_path):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services.rag import index_document, query

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            ("/tmp/reindex.txt", "reindex-hash", "reindex.txt"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Old argon', 'argon plasma baseline evidence', 'body')
            """,
            (document_id,),
        )
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 2, 'Old stale', 'metastable stale evidence', 'body')
            """,
            (document_id,),
        )

    assert index_document(document_id)["status"] == "indexed"
    assert query("metastable", [document_id], 3)["sources"]

    with get_conn() as conn:
        conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM sections WHERE document_id=?", (document_id,))
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'New', 'oxygen plasma fresh evidence', 'body')
            """,
            (document_id,),
        )

    assert index_document(document_id)["status"] == "indexed"
    stale = query("metastable", [document_id], 3)
    fresh = query("oxygen", [document_id], 3)

    assert stale["sources"] == []
    assert fresh["sources"]

    import json

    vector_index = json.loads((tmp_path / "vector-index.json").read_text(encoding="utf-8"))
    assert all("metastable" not in record["text"] for record in vector_index.values())


def test_rag_failed_reindex_removes_stale_vectors_for_document(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.config import get_settings
    from app.db import get_conn
    from app.services.rag import index_document, query

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            ("/tmp/failed-reindex.txt", "failed-reindex-hash", "failed-reindex.txt"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Old stale', 'metastable stale evidence', 'body')
            """,
            (document_id,),
        )

    assert index_document(document_id)["status"] == "indexed"
    assert query("metastable", [document_id], 3)["sources"]

    get_settings.cache_clear()
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")

    failed = index_document(document_id)
    stale = query("metastable", [document_id], 3)

    assert failed["status"] == "failed"
    assert "unsupported embedding model" in failed["error"]
    assert stale["sources"] == []

    import json

    vector_index = json.loads((tmp_path / "vector-index.json").read_text(encoding="utf-8"))
    assert all(record["document_id"] != document_id for record in vector_index.values())


def test_rag_index_without_sections_removes_stale_vectors(tmp_path):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services.rag import index_document, query

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            ("/tmp/no-sections-reindex.txt", "no-sections-reindex", "no-sections-reindex.txt"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Stale', 'metastable stale evidence', 'body')
            """,
            (document_id,),
        )

    assert index_document(document_id)["status"] == "indexed"
    assert query("metastable", [document_id], 3)["sources"]

    with get_conn() as conn:
        conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM sections WHERE document_id=?", (document_id,))

    failed = index_document(document_id)
    stale = query("metastable", [document_id], 3)

    assert failed["status"] == "failed"
    assert "document has no parsed sections" in failed["error"]
    assert stale["sources"] == []
    with get_conn() as conn:
        document = conn.execute("SELECT index_status, index_error FROM documents WHERE id=?", (document_id,)).fetchone()
    assert document["index_status"] == "failed"
    assert "document has no parsed sections" in document["index_error"]

    import json

    vector_index = json.loads((tmp_path / "vector-index.json").read_text(encoding="utf-8"))
    assert all(record["document_id"] != document_id for record in vector_index.values())


def test_rag_index_failure_discards_partial_chunks(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import rag as rag_service
    from app.services.rag import index_document

    class FailingSecondEmbedding:
        model_name = "local-hash"

        def __init__(self):
            self.calls = 0

        def embed(self, text: str) -> list[float]:
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("embedding backend interrupted")
            return rag_service.local_hash_embedding(text)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            ("/tmp/partial-index.txt", "partial-index-hash", "partial-index.txt"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'First', 'argon plasma evidence', 'body')
            """,
            (document_id,),
        )
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 2, 'Second', 'oxygen plasma evidence', 'body')
            """,
            (document_id,),
        )

    monkeypatch.setattr(rag_service, "get_embedding_adapter", lambda _model_name: FailingSecondEmbedding())

    failed = index_document(document_id)

    assert failed["status"] == "failed"
    assert failed["chunks"] == 0
    assert "embedding backend interrupted" in failed["error"]
    with get_conn() as conn:
        chunk_count = conn.execute("SELECT COUNT(*) AS n FROM chunks WHERE document_id=?", (document_id,)).fetchone()["n"]
        document = conn.execute("SELECT index_status, index_error FROM documents WHERE id=?", (document_id,)).fetchone()
    assert chunk_count == 0
    assert document["index_status"] == "failed"
    assert "embedding backend interrupted" in document["index_error"]

    import json

    vector_path = tmp_path / "vector-index.json"
    vector_index = json.loads(vector_path.read_text(encoding="utf-8")) if vector_path.exists() else {}
    assert all(record["document_id"] != document_id for record in vector_index.values())


def test_rag_index_fails_when_sections_have_no_indexable_text(tmp_path):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services.rag import index_document

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            ("/tmp/empty-index.txt", "empty-index", "empty-index.txt"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Empty section', '   ', 'body')
            """,
            (document_id,),
        )

    failed = index_document(document_id)

    assert failed["status"] == "failed"
    assert failed["chunks"] == 0
    assert "document has no indexable section text" in failed["error"]
    with get_conn() as conn:
        document = conn.execute("SELECT index_status, index_error FROM documents WHERE id=?", (document_id,)).fetchone()
        chunk_count = conn.execute("SELECT COUNT(*) AS n FROM chunks WHERE document_id=?", (document_id,)).fetchone()["n"]
    assert chunk_count == 0
    assert document["index_status"] == "failed"
    assert "document has no indexable section text" in document["index_error"]


def test_rag_index_records_failed_status_when_vector_cleanup_fails(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import rag as rag_service
    from app.services.rag import index_document

    class FailingVectorStore:
        def __init__(self, path):
            self.path = path

        def delete_document(self, document_id):
            raise RuntimeError("vector cleanup failed")

    monkeypatch.setattr(rag_service, "JsonVectorStore", FailingVectorStore)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            ("/tmp/vector-cleanup-fail.txt", "vector-cleanup-fail", "vector-cleanup-fail.txt"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Cleanup', 'argon plasma evidence', 'body')
            """,
            (document_id,),
        )

    failed = index_document(document_id)

    assert failed["status"] == "failed"
    assert "vector cleanup failed" in failed["error"]
    with get_conn() as conn:
        document = conn.execute("SELECT index_status, index_error FROM documents WHERE id=?", (document_id,)).fetchone()
    assert document["index_status"] == "failed"
    assert "vector cleanup failed" in document["index_error"]


def test_rag_index_records_failed_status_when_vector_store_json_is_corrupt(tmp_path):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services.rag import index_document

    (tmp_path / "vector-index.json").write_text("{not valid json", encoding="utf-8")
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            ("/tmp/corrupt-vector-store.txt", "corrupt-vector-store", "corrupt-vector-store.txt"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Corrupt vector store', 'argon plasma evidence', 'body')
            """,
            (document_id,),
        )

    failed = index_document(document_id)

    assert failed["status"] == "failed"
    assert "vector store JSON is invalid" in failed["error"]
    with get_conn() as conn:
        document = conn.execute("SELECT index_status, index_error FROM documents WHERE id=?", (document_id,)).fetchone()
        chunk_count = conn.execute("SELECT COUNT(*) AS n FROM chunks WHERE document_id=?", (document_id,)).fetchone()["n"]
    assert chunk_count == 0
    assert document["index_status"] == "failed"
    assert "vector store JSON is invalid" in document["index_error"]


def test_rag_index_rejects_unsupported_vector_db_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("VECTOR_DB_BACKEND", "faiss")
    make_client(tmp_path)

    from app.db import get_conn
    from app.services.rag import index_document

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            ("/tmp/unsupported-vector-backend.txt", "unsupported-vector-backend", "unsupported-vector-backend.txt"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Unsupported backend', 'argon plasma evidence', 'body')
            """,
            (document_id,),
        )

    failed = index_document(document_id)

    assert failed["status"] == "failed"
    assert failed["chunks"] == 0
    assert "unsupported vector db backend: faiss" in failed["error"]
    assert not (tmp_path / "vector-index.json").exists()
    with get_conn() as conn:
        document = conn.execute("SELECT index_status, index_error FROM documents WHERE id=?", (document_id,)).fetchone()
        chunk_count = conn.execute("SELECT COUNT(*) AS n FROM chunks WHERE document_id=?", (document_id,)).fetchone()["n"]
    assert chunk_count == 0
    assert document["index_status"] == "failed"
    assert "unsupported vector db backend: faiss" in document["index_error"]


def test_rag_query_rejects_unsupported_vector_db_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("VECTOR_DB_BACKEND", "faiss")
    make_client(tmp_path)

    import pytest

    from app.services.rag import query

    with pytest.raises(ValueError, match="unsupported vector db backend: faiss"):
        query("argon plasma", [], 3)


def test_reparse_document_clears_stale_downstream_artifacts(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("reparse.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ . argon chemistry"), "application/pdf")},
    )
    document_id = response.json()["id"]

    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/index").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/translate", json={"target_lang": "zh"}).status_code == 202

    assert client.get(f"/api/v1/documents/{document_id}/chunks").json()["total"] > 0
    assert client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["total"] > 0
    assert client.get(f"/api/v1/documents/{document_id}/translation").status_code == 200

    reparsed = client.post(f"/api/v1/documents/{document_id}/parse")
    assert reparsed.status_code == 202

    document = client.get(f"/api/v1/documents/{document_id}").json()
    assert document["parse_status"] == "parsed"
    assert document["index_status"] == "not_indexed"
    assert document["index_error"] is None
    assert document["chemistry_status"] == "not_extracted"
    assert document["chemistry_error"] is None
    assert client.get(f"/api/v1/documents/{document_id}/chunks").json()["total"] == 0
    assert client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["total"] == 0
    assert client.get(f"/api/v1/documents/{document_id}/translation").status_code == 404

    import json

    vector_path = tmp_path / "vector-index.json"
    vector_index = json.loads(vector_path.read_text(encoding="utf-8")) if vector_path.exists() else {}
    assert all(record["document_id"] != document_id for record in vector_index.values())


def test_extract_chemistry_handles_unicode_reaction_arrow(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("unicode-arrow.pdf", pdf_bytes("e + Ar → e + e + Ar+ .".encode("utf-8")), "application/pdf")},
    )
    document_id = response.json()["id"]

    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()

    assert detail["status"] == "pending"
    assert detail["reactions"][0]["reaction"] == "e + Ar -> e + e + Ar+"
    assert detail["reactions"][0]["reactants"] == ["e", "Ar"]
    assert detail["reactions"][0]["products"] == ["e", "e", "Ar+"]


def test_extract_chemistry_handles_unicode_species_subscripts_and_charges(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("unicode-species.pdf", pdf_bytes("e + O₂ → O⁻ + O .".encode("utf-8")), "application/pdf")},
    )
    document_id = response.json()["id"]

    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()

    assert detail["status"] == "pending"
    assert detail["reactions"][0]["reaction"] == "e + O₂ -> O⁻ + O"
    assert detail["reactions"][0]["reactants"] == ["e", "O₂"]
    assert detail["reactions"][0]["products"] == ["O⁻", "O"]


def test_extract_chemistry_handles_compact_reaction_species_separators(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("compact-reaction.pdf", pdf_bytes("e+O₂→O⁻+O .".encode("utf-8")), "application/pdf")},
    )
    document_id = response.json()["id"]

    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()

    assert detail["status"] == "pending"
    assert detail["reactions"][0]["reaction"] == "e + O₂ -> O⁻ + O"
    assert detail["reactions"][0]["reactants"] == ["e", "O₂"]
    assert detail["reactions"][0]["products"] == ["O⁻", "O"]


def test_extract_chemistry_handles_equilibrium_reaction_arrows(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("equilibrium-reaction.pdf", pdf_bytes("e+O₂⇌O₂⁻ .".encode("utf-8")), "application/pdf")},
    )
    document_id = response.json()["id"]

    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()

    assert detail["status"] == "pending"
    assert detail["reactions"][0]["reaction"] == "e + O₂ -> O₂⁻"
    assert detail["reactions"][0]["reactants"] == ["e", "O₂"]
    assert detail["reactions"][0]["products"] == ["O₂⁻"]


def test_reaction_verify_updates_fields_and_records_audit(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("chemistry.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction_id = detail["reactions"][0]["id"]

    verified = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={
            "verified": True,
            "reaction_type": "ionization",
            "rate_type": "cross_section",
            "rate_value": "LXCat original table",
            "threshold_ev": 15.76,
            "cross_section_url": "https://nl.lxcat.net/data/set/example",
            "verified_by": "chemist-a",
        },
    ).json()

    reaction = verified["reactions"][0]
    assert verified["status"] == "verified"
    assert reaction["reaction_type"] == "ionization"
    assert reaction["rate_type"] == "cross_section"
    assert reaction["threshold_ev"] == 15.76
    assert reaction["cross_section_url"] == "https://nl.lxcat.net/data/set/example"
    assert reaction["audit_log"]
    audit = reaction["audit_log"][0]
    assert audit["verified_by"] == "chemist-a"
    assert audit["verified_at"]
    assert audit["verified_at"] == audit["created_at"]
    assert audit["action"] == "verify"
    assert audit["changes"]["reaction_type"] == "ionization"
    assert audit["field_changes"]["reaction_type"] == {"before": "unknown", "after": "ionization"}
    assert audit["field_changes"]["rate_value"] == {"before": None, "after": "LXCat original table"}
    assert audit["field_changes"]["verified"] == {"before": False, "after": True}


def test_reaction_verify_can_clear_optional_review_fields(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("clear-review-fields.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction_id = detail["reactions"][0]["id"]

    client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={
            "verified": True,
            "reaction_type": "ionization",
            "rate_type": "cross_section",
            "rate_value": "LXCat table",
            "threshold_ev": 15.76,
            "cross_section_url": "https://nl.lxcat.net/data/set/example",
            "verified_by": "chemist-a",
        },
    )
    cleared = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={
            "verified": True,
            "reaction_type": None,
            "rate_type": None,
            "rate_value": None,
            "threshold_ev": None,
            "cross_section_url": None,
            "verified_by": "chemist-a",
        },
    ).json()

    reaction = cleared["reactions"][0]
    assert reaction["reaction_type"] is None
    assert reaction["rate_type"] is None
    assert reaction["rate_value"] is None
    assert reaction["threshold_ev"] is None
    assert reaction["cross_section_url"] is None
    assert reaction["audit_log"][0]["changes"]["reaction_type"] is None
    assert reaction["audit_log"][0]["changes"]["rate_type"] is None
    assert reaction["audit_log"][0]["changes"]["rate_value"] is None
    assert reaction["audit_log"][0]["changes"]["threshold_ev"] is None
    assert reaction["audit_log"][0]["changes"]["cross_section_url"] is None


def test_reaction_unverify_returns_reaction_set_to_pending(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("unverify.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction_id = detail["reactions"][0]["id"]

    verified = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={"verified": True, "verified_by": "chemist-a"},
    ).json()
    unverified = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={"verified": False, "verified_by": "chemist-a"},
    ).json()

    assert verified["status"] == "verified"
    assert unverified["status"] == "pending"
    assert unverified["verified_by"] is None
    assert unverified["verified_at"] is None
    assert unverified["reactions"][0]["verified"] is False
    assert unverified["reactions"][0]["audit_log"][0]["action"] == "unverify"


def test_reaction_verify_rejects_blank_verified_by(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("blank-reviewer.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction_id = detail["reactions"][0]["id"]

    rejected = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={"verified": True, "verified_by": "   "},
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"


def test_reaction_verify_requires_reviewer_when_marking_verified(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("missing-reviewer.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction_id = detail["reactions"][0]["id"]

    rejected = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={"verified": True},
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"


def test_reaction_verify_requires_reviewer_when_marking_unverified(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("missing-unverify-reviewer.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction_id = detail["reactions"][0]["id"]
    assert client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={"verified": True, "verified_by": "chemist-a"},
    ).status_code == 200

    rejected = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={"verified": False},
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"


def test_reaction_verify_rejects_blank_rate_value(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("blank-rate.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction_id = detail["reactions"][0]["id"]

    rejected = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={"verified": True, "verified_by": "chemist-a", "rate_value": "   "},
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"


def test_reaction_verify_rejects_negative_threshold_ev(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("negative-threshold.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction_id = detail["reactions"][0]["id"]

    rejected = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={"verified": True, "verified_by": "chemist-a", "threshold_ev": -0.1},
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"


def test_reaction_verify_rejects_invalid_cross_section_url(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("invalid-cross-section-url.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction_id = detail["reactions"][0]["id"]

    rejected = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={"verified": True, "verified_by": "chemist-a", "cross_section_url": "not-a-url"},
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"


def test_reaction_verify_rejects_unknown_rate_type(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("unknown-rate-type.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction_id = detail["reactions"][0]["id"]

    rejected = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={"verified": True, "verified_by": "chemist-a", "rate_type": "magic_rate"},
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"


def test_reaction_verify_rejects_unknown_reaction_type(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("unknown-reaction-type.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction_id = detail["reactions"][0]["id"]

    rejected = client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={"verified": True, "verified_by": "chemist-a", "reaction_type": "magic_reaction"},
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"


def test_reaction_verify_backend_failure_returns_json_error(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.main import app
    from app.routers import reactions as reactions_router
    from fastapi.testclient import TestClient

    def failing_verify_reaction(*args, **kwargs):
        raise RuntimeError("audit database unavailable")

    monkeypatch.setattr(reactions_router, "verify_reaction", failing_verify_reaction)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.put(
        "/api/v1/reactions/123/verify",
        json={"verified": True, "verified_by": "chemist-a"},
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "reaction_verify_failed"
    assert "audit database unavailable" in payload["error"]["message"]


def test_reaction_export_bolsig_text_and_rejects_unknown_format(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("export.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction = detail["reactions"][0]
    reaction_id = reaction["id"]
    client.put(
        f"/api/v1/reactions/{reaction_id}/verify",
        json={
            "verified": True,
            "reaction_type": "ionization",
            "rate_type": "cross_section",
            "rate_value": "original cross section table",
            "threshold_ev": 15.76,
            "cross_section_url": "https://nl.lxcat.net/data/set/example",
            "verified_by": "chemist-a",
        },
    )

    exported = client.post(f"/api/v1/reaction-sets/{reaction_set['id']}/export?format=bolsig").json()
    assert exported["format"] == "bolsig"
    assert exported["mime_type"] == "text/plain"
    text = Path(exported["output_path"]).read_text(encoding="utf-8")
    assert "BOLSIG+" in text
    assert "REACTION: e + Ar -> e + e + Ar" in text
    assert "TYPE: ionization" in text
    assert "RATE_TYPE: cross_section" in text
    assert "THRESHOLD_EV: 15.76" in text
    assert f"CONFIDENCE: {reaction['confidence']}" in text
    assert "CROSS_SECTION_URL: https://nl.lxcat.net/data/set/example" in text
    assert f"SOURCE_SECTION_TITLE: {reaction['source_section_title']}" in text
    assert f"SOURCE_SECTION_TYPE: {reaction['source_section_type']}" in text
    assert f"SOURCE_SECTION_SEQ: {reaction['source_section_seq']}" in text
    assert f"SOURCE_LABEL: {reaction['source_label']}" in text
    assert "VERIFIED_BY: chemist-a" in text
    assert "VERIFIED_AT:" in text

    exported_txt = client.post(f"/api/v1/reaction-sets/{reaction_set['id']}/export?format=txt").json()
    assert exported_txt["output_path"] != exported["output_path"]
    txt = Path(exported_txt["output_path"]).read_text(encoding="utf-8")
    assert f"confidence: {reaction['confidence']}" in txt
    assert f"source_section_title: {reaction['source_section_title']}" in txt
    assert f"source_section_type: {reaction['source_section_type']}" in txt
    assert f"source_section_seq: {reaction['source_section_seq']}" in txt
    assert f"source_label: {reaction['source_label']}" in txt
    assert f"source_excerpt: {reaction['source_excerpt']}" in txt
    assert "verified_by: chemist-a" in txt
    assert "verified_at:" in txt
    assert "BOLSIG+" in Path(exported["output_path"]).read_text(encoding="utf-8")

    invalid = client.post(f"/api/v1/reaction-sets/{reaction_set['id']}/export?format=docx")
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "unsupported_export_format"

    blank = client.post(f"/api/v1/reaction-sets/{reaction_set['id']}/export?format=")
    assert blank.status_code == 400
    assert blank.json()["error"]["code"] == "unsupported_export_format"


def test_reaction_export_rejects_empty_reaction_set(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status, chemistry_status)
            VALUES (?, ?, ?, 'parsed', 'rejected')
            """,
            ("/tmp/empty-reaction-set.pdf", "empty-reaction-set", "empty-reaction-set.pdf"),
        )
        document_id = cursor.lastrowid
        cursor = conn.execute(
            """
            INSERT INTO reaction_sets (document_id, name, source_note, status)
            VALUES (?, 'Empty reaction set', 'No reaction expressions found', 'rejected')
            """,
            (document_id,),
        )
        reaction_set_id = cursor.lastrowid

    response = client.post(f"/api/v1/reaction-sets/{reaction_set_id}/export?format=json")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "reaction_set_unverified"


def test_reaction_export_write_failure_returns_json_error(tmp_path, monkeypatch):
    make_client(tmp_path)

    from pathlib import Path as PathClass

    from app.db import get_conn
    from app.main import app
    from fastapi.testclient import TestClient

    with get_conn() as conn:
        reaction_set_id = conn.execute(
            "INSERT INTO reaction_sets (name, status) VALUES (?, ?)",
            ("Write failure set", "verified"),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO reactions (reaction_set_id, reaction, verified)
            VALUES (?, ?, 1)
            """,
            (reaction_set_id, "e + Ar -> e + e + Ar+"),
        )

    original_write_text = PathClass.write_text

    def failing_write_text(self, *args, **kwargs):
        if self.name == f"reaction-set-{reaction_set_id}.json":
            raise OSError("export disk full")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(PathClass, "write_text", failing_write_text)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(f"/api/v1/reaction-sets/{reaction_set_id}/export?format=json")

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "reaction_export_failed"
    assert "export disk full" in payload["error"]["message"]


def test_release_runbook_artifacts_exist_and_document_commands():
    repo = Path(__file__).resolve().parent.parent
    health_check = repo / "scripts" / "health_check.py"
    env_script = repo / "scripts" / "env.sh"
    dev_script = repo / "scripts" / "dev.sh"
    release_check = repo / "scripts" / "release_check.sh"
    smoke_check = repo / "scripts" / "smoke_check.py"
    validate_env_example = repo / "scripts" / "validate_env_example.py"
    ci_workflow = repo / ".github" / "workflows" / "ci.yml"
    readme = (repo / "README.md").read_text(encoding="utf-8")
    env_example = (repo / ".env.example").read_text(encoding="utf-8")
    config_text = (repo / "app" / "config.py").read_text(encoding="utf-8")

    assert health_check.exists()
    assert "api/v1/system/status?check_external=true" in health_check.read_text(encoding="utf-8")
    assert env_script.exists()
    env_text = env_script.read_text(encoding="utf-8")
    assert "load_env_file_if_unset" in env_text
    assert dev_script.exists()
    dev_text = dev_script.read_text(encoding="utf-8")
    assert 'source "scripts/env.sh"' in dev_text
    assert 'load_env_file_if_unset ".env"' in dev_text
    assert "-m uvicorn app.main:app" in dev_text
    assert "DEV_READY_TIMEOUT" in dev_text
    assert "/api/v1/health" in dev_text
    assert "API failed to become ready" in dev_text
    assert "API process exited before becoming ready" in dev_text
    assert "wait_for_api" in dev_text
    assert '"${API_PID}"' in dev_text
    assert "-m streamlit run streamlit_app.py" in dev_text
    assert "/_stcore/health" in dev_text
    assert "Streamlit failed to become ready" in dev_text
    assert "Streamlit process exited before becoming ready" in dev_text
    assert '"${STREAMLIT_PID}"' in dev_text
    assert ".venv/bin/python" in dev_text
    assert release_check.exists()
    release_text = release_check.read_text(encoding="utf-8")
    assert "set -euo pipefail" in release_text
    assert "rm -rf" not in release_text
    assert "bash -n scripts/env.sh" in release_text
    assert "bash -n scripts/dev.sh" in release_text
    assert "-m py_compile" in release_text
    for compiled_script in [
        "scripts/health_check.py",
        "scripts/import_fixtures.py",
        "scripts/smoke_check.py",
        "scripts/validate_api_contract.py",
        "scripts/validate_docs_links.py",
        "scripts/validate_env_example.py",
        "scripts/validate_readme_commands.py",
        "scripts/validate_release_hygiene.py",
        "scripts/validate_requirements.py",
        "scripts/validate_schema.py",
        "streamlit_app.py",
    ]:
        assert compiled_script in release_text
    assert "scripts/health_check.py --help" in release_text
    assert "scripts/validate_api_contract.py" in release_text
    assert "scripts/validate_docs_links.py" in release_text
    assert "scripts/validate_env_example.py" in release_text
    assert "scripts/validate_readme_commands.py" in release_text
    assert "scripts/validate_release_hygiene.py" in release_text
    assert "scripts/validate_requirements.py" in release_text
    assert "scripts/validate_schema.py" in release_text
    assert "PAPER_LAB_DATA_DIR" in release_text
    assert "VECTOR_DB_BACKEND" in release_text
    assert "TemporaryDirectory" in release_text
    assert "scripts/import_fixtures.py" in release_text
    assert '"documents"' in release_text
    assert "-m scripts.smoke_check" in release_text
    assert "SMOKE_JSON" in release_text
    assert "json.loads" in release_text
    assert "verified_export_format" in release_text
    assert "runtime_version" in release_text
    assert "scheduler_job_ids" in release_text
    assert "config_warning_count" in release_text
    assert "crawl_job_status" in release_text
    assert "crawled_papers" in release_text
    assert '"papers": 2' in release_text
    assert '"paper_categories": 1' in release_text
    assert '"reaction_sets": 1' in release_text
    assert '"reactions": 1' in release_text
    assert "status_counts" in release_text
    assert "sections" in release_text
    assert "chunks" in release_text
    assert "rag_sources" in release_text
    assert "duplicate_upload_status" in release_text
    assert "verified_export_reactions" in release_text
    assert "verified_export_audit_entries" in release_text
    assert "reaction_audits" in release_text
    assert "verified_export_formats" in release_text
    assert "verified_export_text_files" in release_text
    assert "verified_export_bolsig_contains_header" in release_text
    assert "verified_export_txt_contains_reaction" in release_text
    assert "verified_export_txt_has_source_excerpt" in release_text
    assert "rag_answer_has_citation" in release_text
    assert "rag_source_excerpts" in release_text
    assert "verified_export_txt_has_verification_metadata" in release_text
    assert "verified_export_bolsig_has_verification_metadata" in release_text
    assert "-m pytest -q" in release_text
    assert smoke_check.exists()
    assert validate_env_example.exists()
    assert "REQUIRED_ENV_KEYS" in validate_env_example.read_text(encoding="utf-8")
    smoke_text = smoke_check.read_text(encoding="utf-8")
    assert '"VECTOR_DB_BACKEND"] = "local-json"' in smoke_text
    assert "load_fixture_papers" in smoke_text
    assert '"/api/v1/papers?q=plasma"' in smoke_text
    assert '"/api/v1/crawl/run"' in smoke_text
    assert '"crawl_job_status"' in smoke_text
    assert '"crawled_papers"' in smoke_text
    assert '"papers"' in smoke_text
    assert '"paper_categories"' in smoke_text
    assert '"reaction_sets"' in smoke_text
    assert '"reactions"' in smoke_text
    assert '"status_counts"' in smoke_text
    assert '"sections"' in smoke_text
    assert '"chunks"' in smoke_text
    assert '"rag_sources"' in smoke_text
    assert '"duplicate_upload_status"' in smoke_text
    assert '"scheduler_job_ids"' in smoke_text
    assert '"verified_export_reactions"' in smoke_text
    assert '"verified_export_audit_entries"' in smoke_text
    assert '"reaction_audits"' in smoke_text
    assert '"verified_export_formats"' in smoke_text
    assert '"verified_export_text_files"' in smoke_text
    assert '"verified_export_bolsig_contains_header"' in smoke_text
    assert '"verified_export_txt_contains_reaction"' in smoke_text
    assert '"verified_export_txt_has_source_excerpt"' in smoke_text
    assert '"rag_answer_has_citation"' in smoke_text
    assert '"rag_source_excerpts"' in smoke_text
    assert '"verified_export_txt_has_verification_metadata"' in smoke_text
    assert '"verified_export_bolsig_has_verification_metadata"' in smoke_text
    assert '"/api/v1/system/status"' in smoke_text
    assert "runtime_version" in smoke_text
    assert "config_warning_count" in smoke_text
    assert ci_workflow.exists()
    ci_text = ci_workflow.read_text(encoding="utf-8")
    assert "bash scripts/release_check.sh" in ci_text
    for required in [
        "bash scripts/dev.sh",
        "python scripts/health_check.py",
        "python scripts/health_check.py --compact",
        "API_BASE_URL=http://127.0.0.1:8001/api/v1 python scripts/health_check.py",
        "curl http://127.0.0.1:8000/api/v1/system/status",
        "`config_warnings`",
        "docker run --rm -p 8070:8070 lfoppiano/grobid",
        "`--check-external` 会主动检查 GROBID",
        "python scripts/health_check.py --require-grobid",
        "python scripts/import_fixtures.py",
        "python -m scripts.smoke_check",
        "bash scripts/release_check.sh",
        "PAPER_LAB_SCHEDULER_ENABLED=true",
        "翻译、化学抽取、复核闸门和导出",
        "DEV_READY_TIMEOUT",
        "/_stcore/health",
    ]:
        assert required in readme
    for required in [
        "API_HOST",
        "API_PORT",
        "STREAMLIT_HOST",
        "STREAMLIT_PORT",
        "FRONTEND_URL",
        "DEV_READY_TIMEOUT",
        "ACADEMIC_API_MAX_PAGES",
        "ACADEMIC_API_MAX_RETRIES",
        "ACADEMIC_API_RETRY_BACKOFF_SECONDS",
        "ACADEMIC_API_TIMEOUT_SECONDS",
        "UNPAYWALL_API_MAX_RETRIES",
        "UNPAYWALL_API_RETRY_BACKOFF_SECONDS",
        "UNPAYWALL_API_TIMEOUT_SECONDS",
    ]:
        assert required in env_example
    assert "EMBEDDING_MODEL=local-hash" in env_example
    assert "PAPER_LAB_TEST_MODE" not in env_example
    assert 'default="local-hash", alias="EMBEDDING_MODEL"' in config_text
    assert 'alias="ACADEMIC_API_MAX_PAGES"' in config_text
    assert 'alias="ACADEMIC_API_MAX_RETRIES"' in config_text
    assert 'alias="ACADEMIC_API_RETRY_BACKOFF_SECONDS"' in config_text
    assert 'alias="ACADEMIC_API_TIMEOUT_SECONDS"' in config_text
    assert 'alias="UNPAYWALL_API_MAX_RETRIES"' in config_text
    assert 'alias="UNPAYWALL_API_RETRY_BACKOFF_SECONDS"' in config_text
    assert 'alias="UNPAYWALL_API_TIMEOUT_SECONDS"' in config_text


def test_env_loader_preserves_existing_environment_values(tmp_path):
    import subprocess

    repo = Path(__file__).resolve().parent.parent
    env_script = repo / "scripts" / "env.sh"
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "API_PORT=8000",
                "STREAMLIT_PORT=8501",
                'API_BASE_URL="http://127.0.0.1:8000/api/v1"',
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "bash",
            "-c",
            (
                "set -euo pipefail; "
                f"source {env_script}; "
                "export API_PORT=9000; "
                "load_env_file_if_unset .env; "
                'printf "%s|%s|%s" "$API_PORT" "$STREAMLIT_PORT" "$API_BASE_URL"'
            ),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "9000|8501|http://127.0.0.1:8000/api/v1"


def test_dev_api_base_url_tracks_runtime_port_override(tmp_path):
    import subprocess

    repo = Path(__file__).resolve().parent.parent
    env_script = repo / "scripts" / "env.sh"
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "API_HOST=127.0.0.1",
                "API_PORT=8000",
                "API_BASE_URL=http://127.0.0.1:8000/api/v1",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "bash",
            "-c",
            (
                "set -euo pipefail; "
                f"source {env_script}; "
                "export API_PORT=9000; "
                'USER_API_BASE_URL="${API_BASE_URL:-}"; '
                'USER_API_HOST_SET="${API_HOST+x}"; '
                'USER_API_PORT_SET="${API_PORT+x}"; '
                "load_env_file_if_unset .env; "
                'API_HOST="${API_HOST:-127.0.0.1}"; '
                'API_PORT="${API_PORT:-8000}"; '
                'API_BASE_URL="$(resolve_api_base_url "$USER_API_BASE_URL" "$USER_API_HOST_SET" "$USER_API_PORT_SET")"; '
                'printf "%s" "$API_BASE_URL"'
            ),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "http://127.0.0.1:9000/api/v1"


def test_dev_api_base_url_uses_loopback_for_wildcard_bind_host(tmp_path):
    import subprocess

    repo = Path(__file__).resolve().parent.parent
    env_script = repo / "scripts" / "env.sh"

    result = subprocess.run(
        [
            "bash",
            "-c",
            (
                "set -euo pipefail; "
                f"source {env_script}; "
                "export API_HOST=0.0.0.0; "
                "export API_PORT=9000; "
                'USER_API_BASE_URL="${API_BASE_URL:-}"; '
                'USER_API_HOST_SET="${API_HOST+x}"; '
                'USER_API_PORT_SET="${API_PORT+x}"; '
                'API_BASE_URL="$(resolve_api_base_url "$USER_API_BASE_URL" "$USER_API_HOST_SET" "$USER_API_PORT_SET")"; '
                'printf "%s" "$API_BASE_URL"'
            ),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "http://127.0.0.1:9000/api/v1"


def test_system_status_contract_documents_operational_counts():
    repo = Path(__file__).resolve().parent.parent
    api_doc = (repo / "docs" / "接口设计文档.md").read_text(encoding="utf-8")
    system_section = api_doc[api_doc.index("## 模块 0") : api_doc.index("## 模块 A")]

    for required in [
        "version",
        "storage_health",
        "config_warnings",
        "status_counts",
        "categories",
        "paper_categories",
        "crawl_jobs",
        "reaction_sets",
        "reactions",
        "reaction_audits",
    ]:
        assert required in system_section


def test_system_status_counts_reaction_audits(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        document_id = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name)
            VALUES (?, ?, ?)
            """,
            (str(tmp_path / "audit.pdf"), "audit-status", "audit.pdf"),
        ).lastrowid
        reaction_set_id = conn.execute(
            """
            INSERT INTO reaction_sets (document_id, name, status)
            VALUES (?, 'Audit status set', 'pending')
            """,
            (document_id,),
        ).lastrowid
        reaction_id = conn.execute(
            """
            INSERT INTO reactions (reaction_set_id, reaction, verified)
            VALUES (?, 'e + Ar -> e + e + Ar+', 1)
            """,
            (reaction_set_id,),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO reaction_audits (reaction_id, action, changes, verified_by)
            VALUES (?, 'verify', '{}', 'status-test')
            """,
            (reaction_id,),
        )

    payload = client.get("/api/v1/system/status").json()

    assert payload["counts"]["reaction_audits"] == 1


def test_system_status_counts_paper_categories(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        paper_id = conn.execute(
            """
            INSERT INTO papers (doi, title, abstract, authors, source_api, raw_metadata)
            VALUES (?, ?, ?, '[]', 'status-test', '{}')
            """,
            ("10.999/status-paper-category", "Status category paper", "argon plasma chemistry"),
        ).lastrowid
        category_id = conn.execute("SELECT id FROM categories WHERE slug='chemistry'").fetchone()["id"]
        conn.execute(
            """
            INSERT INTO paper_categories (paper_id, category_id, confidence, method)
            VALUES (?, ?, 0.9, 'manual')
            """,
            (paper_id, category_id),
        )

    payload = client.get("/api/v1/system/status").json()

    assert payload["counts"]["paper_categories"] == 1


def test_system_status_reports_workflow_status_counts(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        parsed_document_id = conn.execute(
            """
            INSERT INTO documents (
                file_path, file_hash, original_name,
                parse_status, index_status, chemistry_status
            ) VALUES (?, ?, ?, 'parsed', 'indexed', 'extracted')
            """,
            (str(tmp_path / "parsed.pdf"), "parsed-status", "parsed.pdf"),
        ).lastrowid
        failed_document_id = conn.execute(
            """
            INSERT INTO documents (
                file_path, file_hash, original_name,
                parse_status, index_status, chemistry_status
            ) VALUES (?, ?, ?, 'failed', 'failed', 'failed')
            """,
            (str(tmp_path / "failed.pdf"), "failed-status", "failed.pdf"),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO crawl_jobs (period, status, papers_found, papers_filtered, papers_new)
            VALUES ('manual', 'success', 1, 0, 1)
            """
        )
        conn.execute(
            """
            INSERT INTO crawl_jobs (period, status, error)
            VALUES ('manual', 'failed', 'network timeout')
            """
        )
        conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status)
            VALUES (?, 'en', 'zh', 'done')
            """,
            (parsed_document_id,),
        )
        conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status, error)
            VALUES (?, 'en', 'zh', 'failed', 'model unavailable')
            """,
            (failed_document_id,),
        )
        conn.execute(
            """
            INSERT INTO reaction_sets (document_id, name, status)
            VALUES (?, 'Verified set', 'verified')
            """,
            (parsed_document_id,),
        )
        conn.execute(
            """
            INSERT INTO reaction_sets (document_id, name, status)
            VALUES (?, 'Pending set', 'pending')
            """,
            (failed_document_id,),
        )

    status_counts = client.get("/api/v1/system/status").json()["status_counts"]

    assert status_counts["crawl_jobs"]["success"] == 1
    assert status_counts["crawl_jobs"]["failed"] == 1
    assert status_counts["document_parse"]["parsed"] == 1
    assert status_counts["document_parse"]["failed"] == 1
    assert status_counts["document_index"]["indexed"] == 1
    assert status_counts["document_index"]["failed"] == 1
    assert status_counts["document_chemistry"]["extracted"] == 1
    assert status_counts["document_chemistry"]["failed"] == 1
    assert status_counts["translations"]["done"] == 1
    assert status_counts["translations"]["failed"] == 1
    assert status_counts["reaction_sets"]["verified"] == 1
    assert status_counts["reaction_sets"]["pending"] == 1


def test_reaction_verify_contract_documents_clearable_review_fields():
    repo = Path(__file__).resolve().parent.parent
    api_doc = (repo / "docs" / "接口设计文档.md").read_text(encoding="utf-8")
    chemistry_section = api_doc[api_doc.index("## 模块 H") :]

    for required in [
        "`reaction_type: null`",
        "`rate_type: null`",
        "`rate_value: null`",
        "`threshold_ev: null`",
        "`cross_section_url: null`",
    ]:
        assert required in chemistry_section


def test_health_check_fails_when_system_status_shape_is_invalid(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {"database_path": "/tmp/plasma.db"}

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "system status" in captured.err


def test_health_check_fails_when_runtime_status_is_missing(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_runtime", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "runtime" in captured.err


def test_health_check_requires_runtime_version():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_runtime_version", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    runtime = health_check_runtime()
    runtime.pop("version")
    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": runtime,
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
        }
    )

    assert "runtime missing keys: version" in errors


def test_health_check_requires_scheduler_jobs_runtime_key():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_scheduler_jobs", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    runtime = health_check_runtime()
    runtime.pop("scheduler_jobs")
    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": runtime,
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    assert "runtime missing keys: scheduler_jobs" in errors


def test_health_check_rejects_invalid_scheduler_jobs_shape():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_scheduler_jobs_shape", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": {
                "api_prefix": "/api/v1",
                "scheduler_enabled": False,
                "scheduler_jobs": [
                    {"id": "crawl-daily", "period": "", "trigger": "cron", "schedule": "day=*, hour=2"},
                    "not a job",
                ],
                "version": "0.1.0",
            },
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    joined = "; ".join(errors)
    assert "scheduler_jobs invalid values" in joined
    assert "0.period" in joined
    assert "0.timezone" in joined
    assert "1" in joined


def test_health_check_fails_when_database_path_is_invalid(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_invalid_database_path", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "",
            "runtime": health_check_runtime(),
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "database_path must be a non-empty string" in captured.err


def test_health_check_fails_when_storage_or_capability_keys_are_missing(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_storage", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "storage": {"data_dir": "/tmp/data"},
            "external_capabilities": {"openalex_mailto": True},
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "storage missing keys" in captured.err
    assert "external_capabilities missing keys" in captured.err


def test_health_check_fails_when_storage_values_are_invalid(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_invalid_storage_values", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": 123,
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "storage invalid values" in captured.err
    assert "pdf_dir" in captured.err
    assert "vector_db_path" in captured.err


def test_health_check_fails_when_external_capability_values_are_invalid(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_invalid_capabilities", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": "yes",
                "unpaywall_email": True,
                "grobid_url": "",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": "false",
                "embedding_model": 123,
                "vector_db_backend": 456,
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "external_capabilities invalid values" in captured.err
    assert "openalex_mailto" in captured.err
    assert "grobid_url" in captured.err
    assert "llm_api_key" in captured.err
    assert "embedding_model" in captured.err
    assert "vector_db_backend" in captured.err


def test_health_check_requires_vector_db_backend_capability_key():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_vector_backend_key", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    assert "external_capabilities missing keys: vector_db_backend" in errors


def test_health_check_fails_when_grobid_values_are_invalid(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_invalid_grobid_values", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "", "available": "yes", "status_code": "200", "error": 404},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "grobid invalid values" in captured.err
    assert "url" in captured.err
    assert "available" in captured.err
    assert "status_code" in captured.err
    assert "error" in captured.err


def test_health_check_fails_when_count_values_are_invalid(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_counts", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {
                    "url": "http://127.0.0.1:8070",
                    "available": None,
                    "status_code": None,
                    "error": None,
                },
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(journals="6", papers=-1),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "counts invalid values" in captured.err
    assert "journals" in captured.err
    assert "papers" in captured.err


def test_health_check_requires_operational_count_keys():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_operational_counts", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": {"journals": 6, "papers": 1, "documents": 0},
        }
    )

    assert "counts missing keys" in "; ".join(errors)
    for required in ["categories", "paper_categories", "crawl_jobs", "reaction_sets", "reactions", "reaction_audits"]:
        assert required in "; ".join(errors)


def test_health_check_requires_config_warnings_key():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_config_warning_key", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    assert "missing keys: config_warnings" in errors


def test_health_check_requires_status_counts_key():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_status_counts_key", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
        }
    )

    assert "missing keys: status_counts" in errors


def test_health_check_requires_storage_health_key():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_storage_health_key", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    assert "missing keys: storage_health" in errors


def test_health_check_requires_database_file_health():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_database_health", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    storage_health = health_check_storage_health()
    storage_health.pop("database", None)
    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": storage_health,
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    assert "storage_health missing keys: database" in errors


def test_health_check_rejects_database_health_path_mismatch():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_database_health_path", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(
                database={"path": "/tmp/other.db", "exists": True, "writable": True},
            ),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    joined = "; ".join(errors)
    assert "storage_health invalid values" in joined
    assert "database.path must match database_path" in joined


def test_health_check_rejects_invalid_storage_health_shape():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_storage_health_shape", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage_health": health_check_storage_health(
                data_dir={"path": "", "exists": True, "writable": True},
                pdf_dir={"path": "/tmp/data/pdfs", "exists": "yes", "writable": True},
                database_parent="not an object",
            ),
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    joined = "; ".join(errors)
    assert "storage_health invalid values" in joined
    assert "data_dir.path" in joined
    assert "pdf_dir.exists" in joined
    assert "database_parent" in joined


def test_health_check_rejects_storage_health_path_mismatch():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_storage_health_path", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage_health": health_check_storage_health(
                data_dir={"path": "/tmp/other-data", "exists": True, "writable": True},
            ),
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    joined = "; ".join(errors)
    assert "storage_health invalid values" in joined
    assert "data_dir.path must match storage.data_dir" in joined


def test_health_check_rejects_corrupt_vector_store_health():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_vector_store_health", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage_health": health_check_storage_health(
                vector_db={
                    "path": "/tmp/data/vector-index.json",
                    "exists": True,
                    "readable": True,
                    "writable": True,
                    "valid_json": False,
                    "error": "Expecting property name enclosed in double quotes",
                },
            ),
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    joined = "; ".join(errors)
    assert "storage_health invalid values" in joined
    assert "vector_db.valid_json" in joined
    assert "Expecting property name enclosed in double quotes" in joined


def test_health_check_rejects_vector_store_health_path_mismatch():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_vector_store_health_path", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage_health": health_check_storage_health(
                vector_db={
                    "path": "/tmp/other/vector-index.json",
                    "exists": False,
                    "readable": False,
                    "writable": False,
                    "valid_json": None,
                    "error": None,
                },
            ),
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    joined = "; ".join(errors)
    assert "storage_health invalid values" in joined
    assert "vector_db.path must match storage.vector_db_path" in joined


def test_health_check_rejects_invalid_config_warning_shape():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_config_warning_shape", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [
                {"code": "missing_llm_api_key", "capability": "", "message": "LLM_API_KEY is not configured."},
                "not an object",
            ],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    joined = "; ".join(errors)
    assert "config_warnings invalid values" in joined
    assert "0.capability" in joined
    assert "1" in joined


def test_health_check_fails_when_grobid_status_keys_are_missing(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_grobid", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": False, "error": "connection refused"},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "grobid missing keys" in captured.err
    assert "status_code" in captured.err


def test_health_check_fails_cleanly_when_health_response_is_not_object(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_non_object", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float):
        if url.endswith("/api/v1/health"):
            return ["ok"]
        return {
            "database_path": "/tmp/plasma.db",
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {
                    "url": "http://127.0.0.1:8070",
                    "available": None,
                    "status_code": None,
                    "error": None,
                },
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "health response must be an object" in captured.err


def test_health_check_fails_when_health_service_is_unexpected(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_unexpected_service", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float):
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "other-service"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {
                    "url": "http://127.0.0.1:8070",
                    "available": None,
                    "status_code": None,
                    "error": None,
                },
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "health service must be paper-lab-agent" in captured.err


def test_health_check_accepts_valid_system_status(monkeypatch):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_valid", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {
                    "url": "http://127.0.0.1:8070",
                    "available": None,
                    "status_code": None,
                    "error": None,
                },
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 0


def test_health_check_require_storage_writable_fails_when_storage_is_unwritable(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_require_storage_writable", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(
                pdf_dir={"path": "/tmp/data/pdfs", "exists": True, "writable": False}
            ),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test", "--require-storage-writable"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "storage is not writable" in captured.err
    assert "pdf_dir.writable" in captured.err


def test_health_check_require_storage_writable_allows_missing_vector_store_when_parent_is_writable(monkeypatch):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_require_storage_missing_vector", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test", "--require-storage-writable"])

    assert health_check.main() == 0


def test_health_check_outputs_config_warnings(monkeypatch, capsys):
    import importlib.util
    import json
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_config_warnings", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [
                {
                    "code": "missing_llm_api_key",
                    "capability": "llm_translation",
                    "message": "LLM_API_KEY is not configured.",
                }
            ],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {
                    "url": "http://127.0.0.1:8070",
                    "available": None,
                    "status_code": None,
                    "error": None,
                },
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test", "--compact"])

    assert health_check.main() == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["config_warnings"] == [
        {
            "code": "missing_llm_api_key",
            "capability": "llm_translation",
            "message": "LLM_API_KEY is not configured.",
        }
    ]


def test_health_check_compact_outputs_single_line_json(monkeypatch, capsys):
    import importlib.util
    import json
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_compact", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test", "--compact"])

    assert health_check.main() == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["health"]["service"] == "paper-lab-agent"
    assert payload["status"]["runtime"]["api_prefix"] == "/api/v1"
    assert captured.out.count("\n") == 1
    assert "\n  " not in captured.out


def test_health_check_can_include_streamlit_frontend_probe(monkeypatch, capsys):
    import importlib.util
    import json
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_frontend", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)
    seen_frontend_urls = []

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    def fake_fetch_status(url: str, timeout: float) -> int:
        seen_frontend_urls.append(url)
        return 200

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(health_check, "fetch_status", fake_fetch_status, raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "health_check.py",
            "--base-url",
            "http://api.test",
            "--check-frontend",
            "--frontend-url",
            "http://ui.test",
            "--compact",
        ],
    )

    assert health_check.main() == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert seen_frontend_urls == ["http://ui.test/_stcore/health"]
    assert payload["frontend"] == {"url": "http://ui.test/_stcore/health", "status_code": 200}


def test_health_check_check_frontend_fails_when_streamlit_is_unhealthy(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_frontend_unhealthy", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    def fake_fetch_status(url: str, timeout: float) -> int:
        return 503

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(health_check, "fetch_status", fake_fetch_status, raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        ["health_check.py", "--base-url", "http://api.test", "--check-frontend", "--frontend-url", "http://ui.test"],
    )

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "Streamlit frontend is unavailable" in captured.err
    assert "status_code=503" in captured.err


def test_health_check_check_frontend_reports_connection_error(monkeypatch, capsys):
    import importlib.util
    import json
    import sys
    from urllib.error import URLError

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_frontend_error", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    def fake_fetch_json(url: str, timeout: float) -> dict:
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    def fake_fetch_status(url: str, timeout: float) -> int:
        raise URLError("connection refused")

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(health_check, "fetch_status", fake_fetch_status)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "health_check.py",
            "--base-url",
            "http://api.test",
            "--check-frontend",
            "--frontend-url",
            "http://ui.test",
            "--compact",
        ],
    )

    assert health_check.main() == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["frontend"] == {
        "url": "http://ui.test/_stcore/health",
        "status_code": None,
        "error": "<urlopen error connection refused>",
    }
    assert "Streamlit frontend is unavailable" in captured.err
    assert "connection refused" in captured.err


def test_health_check_require_grobid_fails_when_external_grobid_is_unavailable(monkeypatch, capsys):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_require_grobid", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)
    seen_urls = []

    def fake_fetch_json(url: str, timeout: float) -> dict:
        seen_urls.append(url)
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {
                    "url": "http://127.0.0.1:8070",
                    "available": False,
                    "status_code": None,
                    "error": "connection refused",
                },
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test", "--require-grobid"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "GROBID is required but unavailable" in captured.err
    assert seen_urls == [
        "http://api.test/api/v1/health",
        "http://api.test/api/v1/system/status?check_external=true",
    ]


def test_health_check_uses_api_base_url_from_env_file(monkeypatch, tmp_path):
    import importlib.util
    import sys

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_env_file", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    (tmp_path / ".env").write_text("API_BASE_URL=http://api.test:9001/api/v1 # local health target\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    seen_urls = []

    def fake_fetch_json(url: str, timeout: float) -> dict:
        seen_urls.append(url)
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(),
            "config_warnings": [],
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py"])

    assert health_check.main() == 0
    assert seen_urls == [
        "http://api.test:9001/api/v1/health",
        "http://api.test:9001/api/v1/system/status",
    ]


def test_health_check_env_value_parser_preserves_unquoted_hashes():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_env_value_parser", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    assert health_check.clean_env_value("8001 # local override") == "8001"
    assert health_check.clean_env_value("sk-test#not-comment # inline comment") == "sk-test#not-comment"
    assert health_check.clean_env_value("http://ui.test/#/papers # inline comment") == "http://ui.test/#/papers"
    assert health_check.clean_env_value('"sk-test#quoted" # inline comment') == "sk-test#quoted"


def test_health_check_env_loader_ignores_invalid_key_names(monkeypatch, tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_env_key_parser", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "API_PORT=8001",
                "BAD KEY=bad",
                "1BAD=bad",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("API_PORT", raising=False)
    monkeypatch.delenv("BAD KEY", raising=False)
    monkeypatch.delenv("1BAD", raising=False)

    health_check.load_env_file(env_file)

    assert os.environ["API_PORT"] == "8001"
    assert "BAD KEY" not in os.environ
    assert "1BAD" not in os.environ


def test_health_check_rejects_unexpected_api_prefix():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "health_check.py"
    spec = importlib.util.spec_from_file_location("health_check_script_api_prefix", script_path)
    assert spec is not None
    assert spec.loader is not None
    health_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(health_check)

    errors = health_check.validate_system_status(
        {
            "database_path": "/tmp/plasma.db",
            "runtime": health_check_runtime(api_prefix="/wrong-prefix"),
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "storage_health": health_check_storage_health(),
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
                "vector_db_backend": "local-json",
            },
            "counts": health_check_counts(),
            "status_counts": health_check_status_counts(),
        }
    )

    assert "runtime api_prefix must be /api/v1" in errors


def test_streamlit_chemistry_review_ui_exposes_review_fields():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    chemistry_section = streamlit[streamlit.index("with chemistry_tab:") :]
    for required in [
        "reaction_type",
        "rate_type",
        "rate_value",
        "threshold_ev",
        "confidence",
        "source_section_id",
        "source_section_title",
        "source_section_type",
        "source_section_seq",
        "source_label",
        "source_excerpt",
        "cross_section_url",
        "verified_by",
        "audit_log",
        "chemistry_document_id",
        "document_reaction_sets",
        "/documents/{chemistry_document_id}/reaction-sets",
        "unverified_reactions",
        "show_only_unverified",
        "export_blocked",
        "disabled=export_blocked",
        "detail.get('verified_by')",
        "detail.get('verified_at')",
        "detail.get('gas_mixture')",
        "detail.get('lxcat_db')",
        "detail.get('source_note')",
        "未全复核不可导出",
        "未复核",
        "bolsig",
        "format={export_format}",
    ]:
        assert required in chemistry_section


def test_streamlit_chemistry_export_surfaces_file_and_metadata_status():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    chemistry_section = streamlit[streamlit.index("with chemistry_tab:") :]

    for required in [
        'export_path = Path(payload["output_path"])',
        "export_path.exists()",
        "下载导出文件",
        "导出文件不存在",
        'payload.get("reaction_count")',
        'payload.get("audit_entry_count")',
        'payload.get("mime_type")',
    ]:
        assert required in chemistry_section


def test_streamlit_chemistry_tab_can_select_document_for_reaction_sets():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    chemistry_section = streamlit[streamlit.index("with chemistry_tab:") :]

    for required in [
        'chemistry_documents = chemistry_documents_response["items"]',
        'selected_chemistry_document = st.selectbox(',
        "chemistry_document_options",
        "selected_chemistry_document[\"id\"]",
        "暂无可选文档",
        "手动 document_id",
    ]:
        assert required in chemistry_section


def test_streamlit_chemistry_tab_exposes_document_pagination_controls():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    chemistry_section = streamlit[streamlit.index("with chemistry_tab:") :]

    for required in [
        "chemistry_documents_page = chemistry_documents_page_col.number_input(",
        '"chemistry_documents_page"',
        "chemistry_documents_page_size = chemistry_documents_page_size_col.number_input(",
        '"chemistry_documents_page_size"',
        "chemistry_documents_response = api_get(",
        '"/documents"',
        "page=int(chemistry_documents_page)",
        "page_size=int(chemistry_documents_page_size)",
        'chemistry_documents = chemistry_documents_response["items"]',
        "chemistry_documents_response['page']",
        "chemistry_documents_response['page_size']",
        "chemistry_documents_response['total']",
    ]:
        assert required in chemistry_section


def test_streamlit_chemistry_tab_exposes_reaction_set_pagination_controls():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    chemistry_section = streamlit[streamlit.index("with chemistry_tab:") :]

    for required in [
        "reaction_sets_page = reaction_sets_page_col.number_input(",
        '"reaction_sets_page"',
        "reaction_sets_page_size = reaction_sets_page_size_col.number_input(",
        '"reaction_sets_page_size"',
        'st.session_state["document_reaction_sets"] = api_get(',
        'f"/documents/{chemistry_document_id}/reaction-sets"',
        "page=int(reaction_sets_page)",
        "page_size=int(reaction_sets_page_size)",
        "document_reaction_sets['page']",
        "document_reaction_sets['page_size']",
        "document_reaction_sets['total']",
    ]:
        assert required in chemistry_section


def test_streamlit_chemistry_audit_log_surfaces_field_changes():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    chemistry_section = streamlit[streamlit.index("with chemistry_tab:") :]

    for required in [
        "field_changes",
        "field_change_rows",
        '"field"',
        '"before"',
        '"after"',
        "st.dataframe(field_change_rows",
    ]:
        assert required in chemistry_section


def test_streamlit_chemistry_review_surfaces_save_success_state():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    chemistry_section = streamlit[streamlit.index("with chemistry_tab:") :]

    for required in [
        'review_message = st.session_state.pop("reaction_review_message", None)',
        "if review_message:",
        "st.success(review_message)",
    ]:
        assert required in streamlit

    for required in [
        'st.session_state["reaction_review_message"] = "已保存复核结果"',
        "st.rerun()",
    ]:
        assert required in chemistry_section


def test_streamlit_chemistry_export_offers_download():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    chemistry_section = streamlit[streamlit.index("with chemistry_tab:") :]

    for required in [
        "export_path = Path(payload[\"output_path\"])",
        "export_text",
        "st.download_button",
        "下载导出文件",
        'mime=payload.get("mime_type")',
        "file_name=export_path.name",
    ]:
        assert required in chemistry_section


def test_streamlit_chemistry_review_uses_controlled_type_options():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    chemistry_section = streamlit[streamlit.index("with chemistry_tab:") :]

    for required in [
        'reaction_type_options = ["", "elastic", "excitation", "ionization", "attachment", "recombination"]',
        'rate_type_options = ["", "cross_section", "arrhenius", "constant"]',
        'reaction_type_value = reaction.get("reaction_type") or ""',
        'rate_type_value = reaction.get("rate_type") or ""',
        'if reaction_type_value == "unknown":',
        'if rate_type_value == "unknown":',
        'c1.selectbox(',
        'c2.selectbox(',
        '"reaction_type": reaction_type or None',
        '"rate_type": rate_type or None',
    ]:
        assert required in chemistry_section


def test_streamlit_chemistry_review_can_preserve_zero_threshold():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    chemistry_section = streamlit[streamlit.index("with chemistry_tab:") :]

    for required in [
        'include_threshold_ev = c3.checkbox(',
        '"include_threshold_ev"',
        'value=reaction.get("threshold_ev") is not None',
        "threshold_ev_value = (",
        'float(reaction["threshold_ev"]) if reaction.get("threshold_ev") is not None else 0.0',
        'disabled=not include_threshold_ev',
        '"threshold_ev": threshold_ev if include_threshold_ev else None',
    ]:
        assert required in chemistry_section

    assert '"threshold_ev": threshold_ev if threshold_ev else None' not in chemistry_section


def test_streamlit_chemistry_export_blocks_empty_reaction_sets():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    chemistry_section = streamlit[streamlit.index("with chemistry_tab:") :]

    for required in [
        "no_reactions = not reactions",
        "export_blocked = no_reactions or bool(unverified_reactions)",
        "if no_reactions:",
        "没有可导出的反应。",
        "elif export_blocked:",
        "disabled=export_blocked",
    ]:
        assert required in chemistry_section


def test_streamlit_chemistry_document_reaction_sets_show_empty_state():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    chemistry_section = streamlit[streamlit.index("with chemistry_tab:") :]

    assert "该文档暂无反应集。" in chemistry_section


def test_document_chunks_endpoint_reports_index_status(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("chunks.pdf", pdf_bytes(b"Argon plasma chemistry. Electron impact reactions."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202

    before = client.get(f"/api/v1/documents/{document_id}/chunks").json()
    assert before["total"] == 0
    assert before["indexed"] is False

    assert client.post(f"/api/v1/documents/{document_id}/index").status_code == 202
    after = client.get(f"/api/v1/documents/{document_id}/chunks").json()
    assert after["indexed"] is True
    assert after["total"] >= 1
    assert after["items"][0]["vector_id"]
    assert after["items"][0]["section_title"]
    empty_page = client.get(
        f"/api/v1/documents/{document_id}/chunks",
        params={"page": after["total"] + 1, "page_size": 1},
    ).json()
    assert empty_page["items"] == []
    assert empty_page["total"] == after["total"]
    assert empty_page["indexed"] is True
    assert empty_page["index_status"] == "indexed"


def test_document_chunks_endpoint_orders_by_section_then_chunk_sequence(tmp_path):
    client = make_client(tmp_path)

    from app.db import get_conn

    with get_conn() as conn:
        document_id = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status, index_status)
            VALUES (?, ?, ?, 'parsed', 'indexed')
            """,
            ("/tmp/chunk-order.pdf", "chunk-order", "chunk-order.pdf"),
        ).lastrowid
        later_section_id = conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 2, 'Later section', 'later evidence', 'body')
            """,
            (document_id,),
        ).lastrowid
        earlier_section_id = conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Earlier section', 'earlier evidence', 'body')
            """,
            (document_id,),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO chunks (document_id, section_id, seq, text, token_count, vector_id, embedded)
            VALUES (?, ?, 1, 'later chunk', 2, 'later-vector', 1)
            """,
            (document_id, later_section_id),
        )
        conn.execute(
            """
            INSERT INTO chunks (document_id, section_id, seq, text, token_count, vector_id, embedded)
            VALUES (?, ?, 1, 'earlier chunk', 2, 'earlier-vector', 1)
            """,
            (document_id, earlier_section_id),
        )

    chunks = client.get(f"/api/v1/documents/{document_id}/chunks").json()

    assert [item["section_title"] for item in chunks["items"]] == ["Earlier section", "Later section"]


def test_document_index_route_clears_stale_chunks_before_background_task_runs(tmp_path):
    from fastapi import BackgroundTasks

    client = make_client(tmp_path)

    from app.db import get_conn
    from app.routers import documents as document_router

    with get_conn() as conn:
        document_id = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status, index_status)
            VALUES (?, ?, ?, 'parsed', 'indexed')
            """,
            (str(tmp_path / "queued-index.pdf"), "queued-index", "queued-index.pdf"),
        ).lastrowid
        section_id = conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Parsed section', 'fresh parsed text', 'body')
            """,
            (document_id,),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO chunks (document_id, section_id, seq, text, token_count, vector_id, embedded)
            VALUES (?, ?, 1, 'old indexed text', 3, 'old-vector', 1)
            """,
            (document_id, section_id),
        )

    index_payload = document_router.index(document_id, BackgroundTasks())
    chunks = client.get(f"/api/v1/documents/{document_id}/chunks").json()

    assert index_payload["document_id"] == document_id
    assert index_payload["index_status"] == "indexing"
    assert chunks["index_status"] == "indexing"
    assert chunks["index_error"] is None
    assert chunks["total"] == 0


def test_document_extract_route_clears_stale_reaction_sets_before_background_task_runs(tmp_path):
    from fastapi import BackgroundTasks

    client = make_client(tmp_path)

    from app.db import get_conn
    from app.routers import documents as document_router

    with get_conn() as conn:
        document_id = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status, chemistry_status)
            VALUES (?, ?, ?, 'parsed', 'extracted')
            """,
            (str(tmp_path / "queued-extract.pdf"), "queued-extract", "queued-extract.pdf"),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Parsed section', 'e + Ar -> e + e + Ar+ .', 'body')
            """,
            (document_id,),
        )
        conn.execute(
            """
            INSERT INTO reaction_sets (document_id, name, source_note, status)
            VALUES (?, 'Old reaction set', 'old extraction', 'pending')
            """,
            (document_id,),
        )

    extract_payload = document_router.extract_chemistry(document_id, BackgroundTasks())
    reaction_sets = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()

    assert extract_payload["document_id"] == document_id
    assert extract_payload["chemistry_status"] == "extracting"
    assert reaction_sets["total"] == 0


def test_document_async_routes_mark_queued_status_before_background_tasks_run(tmp_path):
    from fastapi import BackgroundTasks

    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("queued.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]

    from app.routers import documents as document_router
    from app.db import get_conn

    with get_conn() as conn:
        section_id = conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Old section', 'old parsed text', 'body')
            """,
            (document_id,),
        ).lastrowid
        conn.execute(
            """
            INSERT INTO chunks (document_id, section_id, seq, text, token_count, vector_id, embedded)
            VALUES (?, ?, 1, 'old parsed text', 3, 'old-vector', 1)
            """,
            (document_id, section_id),
        )
        conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status, output_path)
            VALUES (?, 'en', 'zh', 'done', ?)
            """,
            (document_id, str(tmp_path / "translations" / "old.md")),
        )
        conn.execute(
            """
            INSERT INTO reaction_sets (document_id, name, source_note, status)
            VALUES (?, 'Old reaction set', 'old extraction', 'pending')
            """,
            (document_id,),
        )
        conn.execute(
            """
            UPDATE documents
            SET index_status='indexed',
                index_error='old index error',
                chemistry_status='extracted',
                chemistry_error='old chemistry error'
            WHERE id=?
            """,
            (document_id,),
        )

    parse_payload = document_router.parse(document_id, BackgroundTasks())
    assert parse_payload["document_id"] == document_id
    assert parse_payload["parse_status"] == "parsing"
    document = client.get(f"/api/v1/documents/{document_id}").json()
    assert document["parse_status"] == "parsing"
    assert document["parse_error"] is None
    assert document["index_status"] == "not_indexed"
    assert document["index_error"] is None
    assert document["chemistry_status"] == "not_extracted"
    assert document["chemistry_error"] is None
    assert client.get(f"/api/v1/documents/{document_id}/sections").json()["total"] == 0
    assert client.get(f"/api/v1/documents/{document_id}/chunks").json()["total"] == 0
    assert client.get(f"/api/v1/documents/{document_id}/translation").status_code == 404
    assert client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["total"] == 0

    document_router.translate(document_id, document_router.TranslateIn(target_lang="zh"), BackgroundTasks())
    translation = client.get(f"/api/v1/documents/{document_id}/translation").json()
    assert translation["status"] == "pending"
    assert translation["target_lang"] == "zh"

    index_payload = document_router.index(document_id, BackgroundTasks())
    assert index_payload["document_id"] == document_id
    assert index_payload["index_status"] == "indexing"
    chunks = client.get(f"/api/v1/documents/{document_id}/chunks").json()
    assert chunks["index_status"] == "indexing"
    assert chunks["index_error"] is None

    extract_payload = document_router.extract_chemistry(document_id, BackgroundTasks())
    assert extract_payload["document_id"] == document_id
    assert extract_payload["chemistry_status"] == "extracting"
    document = client.get(f"/api/v1/documents/{document_id}").json()
    assert document["chemistry_status"] == "extracting"
    assert document["chemistry_error"] is None


def test_extracted_reaction_keeps_source_section_and_excerpt(tmp_path):
    client = make_client(tmp_path)
    content = pdf_bytes(b"Section text before. e + Ar -> e + e + Ar+ . Section text after.")
    response = client.post(
        "/api/v1/documents",
        files={"file": ("source-trace.pdf", content, "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    sections = client.get(f"/api/v1/documents/{document_id}/sections").json()["items"]
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction = detail["reactions"][0]

    assert reaction["source_section_id"] == sections[0]["id"]
    assert reaction["source_section_title"] == sections[0]["title"]
    assert reaction["source_section_type"] == sections[0]["section_type"]
    assert reaction["source_section_seq"] == sections[0]["seq"]
    assert reaction["source_label"] == f"{sections[0]['section_type']} {sections[0]['seq']}: {sections[0]['title']}"
    assert "e + Ar -> e + e + Ar" in reaction["source_excerpt"]
    assert "Section text before" in reaction["source_excerpt"]
    assert reaction["reactants"] == ["e", "Ar"]
    assert reaction["products"] == ["e", "e", "Ar+"]


def test_extract_chemistry_rerun_replaces_previous_reaction_set(tmp_path):
    client = make_client(tmp_path)
    content = pdf_bytes(b"Ar/O2 chemistry. e + Ar -> e + e + Ar+ .")
    response = client.post(
        "/api/v1/documents",
        files={"file": ("rerun-extract.pdf", content, "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    first = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()

    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202
    second = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()

    assert first["total"] == 1
    assert second["total"] == 1
    detail = client.get(f"/api/v1/reaction-sets/{second['items'][0]['id']}").json()
    assert len(detail["reactions"]) == 1
    assert detail["reactions"][0]["reaction"] == "e + Ar -> e + e + Ar+"


def test_extract_chemistry_failure_marks_document_failed_and_discards_partial_sets(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    content = pdf_bytes(b"Ar/O2 chemistry. e + Ar -> e + e + Ar+ .")
    response = client.post(
        "/api/v1/documents",
        files={"file": ("extract-failure.pdf", content, "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202

    from app.db import get_conn
    from app.services import chemistry as chemistry_service

    def broken_normalize_reaction(reaction):
        raise RuntimeError("chemistry parser interrupted")

    monkeypatch.setattr(chemistry_service, "normalize_reaction", broken_normalize_reaction)

    result = chemistry_service.extract_reactions(document_id)

    assert result["status"] == "failed"
    assert "chemistry parser interrupted" in result["error"]
    with get_conn() as conn:
        document = conn.execute(
            "SELECT chemistry_status, chemistry_error FROM documents WHERE id=?",
            (document_id,),
        ).fetchone()
        reaction_sets = conn.execute("SELECT * FROM reaction_sets WHERE document_id=?", (document_id,)).fetchall()
    assert document["chemistry_status"] == "failed"
    assert "chemistry parser interrupted" in document["chemistry_error"]
    assert reaction_sets == []


def test_extract_chemistry_fails_when_sections_have_no_text(tmp_path):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import chemistry as chemistry_service

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            ("/tmp/empty-chemistry.txt", "empty-chemistry", "empty-chemistry.txt"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Empty chemistry', '   ', 'body')
            """,
            (document_id,),
        )

    result = chemistry_service.extract_reactions(document_id)

    assert result["status"] == "failed"
    assert "document has no extractable section text" in result["error"]
    with get_conn() as conn:
        document = conn.execute(
            "SELECT chemistry_status, chemistry_error FROM documents WHERE id=?",
            (document_id,),
        ).fetchone()
        reaction_sets = conn.execute("SELECT * FROM reaction_sets WHERE document_id=?", (document_id,)).fetchall()
    assert document["chemistry_status"] == "failed"
    assert "document has no extractable section text" in document["chemistry_error"]
    assert reaction_sets == []


def test_extract_chemistry_without_sections_clears_stale_reaction_sets(tmp_path):
    make_client(tmp_path)

    from app.db import get_conn
    from app.services import chemistry as chemistry_service

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            ("/tmp/no-sections-chemistry.txt", "no-sections-chemistry", "no-sections-chemistry.txt"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO reaction_sets (document_id, name, source_note, status)
            VALUES (?, 'Stale reaction set', 'Old extraction', 'pending')
            """,
            (document_id,),
        )

    result = chemistry_service.extract_reactions(document_id)

    assert result["status"] == "failed"
    assert "document has no parsed sections" in result["error"]
    with get_conn() as conn:
        document = conn.execute(
            "SELECT chemistry_status, chemistry_error FROM documents WHERE id=?",
            (document_id,),
        ).fetchone()
        reaction_sets = conn.execute("SELECT * FROM reaction_sets WHERE document_id=?", (document_id,)).fetchall()
    assert document["chemistry_status"] == "failed"
    assert "document has no parsed sections" in document["chemistry_error"]
    assert reaction_sets == []


def test_extract_reactions_detects_lxcat_database_and_url(tmp_path):
    client = make_client(tmp_path)
    content = pdf_bytes(
        b"LXCat Biagi database cross section: https://nl.lxcat.net/data/set/biagi. "
        b"The process is e + Ar -> e + e + Ar+ ."
    )
    response = client.post(
        "/api/v1/documents",
        files={"file": ("lxcat.pdf", content, "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202

    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()
    reaction = detail["reactions"][0]

    assert detail["lxcat_db"] == "Biagi"
    assert reaction["reaction"] == "e + Ar -> e + e + Ar+"
    assert reaction["reactants"] == ["e", "Ar"]
    assert reaction["products"] == ["e", "e", "Ar+"]
    assert reaction["cross_section_url"] == "https://nl.lxcat.net/data/set/biagi"


def test_extract_reactions_detects_explicit_gas_mixture(tmp_path):
    client = make_client(tmp_path)
    content = pdf_bytes(b"The Ar/O2 plasma chemistry includes e + O2 -> O- + O .")
    response = client.post(
        "/api/v1/documents",
        files={"file": ("gas-mixture.pdf", content, "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    assert client.post(f"/api/v1/documents/{document_id}/extract-chemistry").status_code == 202

    reaction_set = client.get(f"/api/v1/documents/{document_id}/reaction-sets").json()["items"][0]
    detail = client.get(f"/api/v1/reaction-sets/{reaction_set['id']}").json()

    assert detail["gas_mixture"] == "Ar/O2"
    assert detail["reactions"][0]["reaction"] == "e + O2 -> O- + O"


def test_translate_unparsed_document_records_failed_status(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("unparsed.pdf", pdf_bytes(b"Needs parsing before translation."), "application/pdf")},
    )
    document_id = response.json()["id"]

    accepted = client.post(f"/api/v1/documents/{document_id}/translate", json={"target_lang": "zh"})
    assert accepted.status_code == 202
    translation = client.get(f"/api/v1/documents/{document_id}/translation").json()
    assert translation["status"] == "failed"
    assert "no parsed sections" in translation["error"]


def test_translate_rejects_blank_target_lang(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("blank-target.pdf", pdf_bytes(b"Needs a target language."), "application/pdf")},
    )
    document_id = response.json()["id"]

    rejected = client.post(f"/api/v1/documents/{document_id}/translate", json={"target_lang": "   "})

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"


def test_translate_normalizes_target_lang_before_creating_job(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("target-normalized.pdf", pdf_bytes(b"Translate this plasma paragraph."), "application/pdf")},
    )
    document_id = response.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202

    accepted = client.post(f"/api/v1/documents/{document_id}/translate", json={"target_lang": " zh-CN "})

    assert accepted.status_code == 202
    assert accepted.json()["target_lang"] == "zh-CN"
    translation = client.get(f"/api/v1/documents/{document_id}/translation").json()
    assert translation["target_lang"] == "zh-CN"
    assert Path(translation["output_path"]).name == f"document-{document_id}-zh-CN.md"


def test_translate_rejects_path_like_target_lang(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("path-target.pdf", pdf_bytes(b"Reject unsafe target language."), "application/pdf")},
    )
    document_id = response.json()["id"]

    rejected = client.post(f"/api/v1/documents/{document_id}/translate", json={"target_lang": "zh/CN"})

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"


def test_translate_document_uses_filesystem_safe_target_lang_slug(tmp_path):
    make_client(tmp_path)
    from app.db import get_conn
    from app.services import translation as translation_service

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (file_path, file_hash, original_name, parse_status)
            VALUES (?, ?, ?, 'parsed')
            """,
            (str(tmp_path / "target-lang.pdf"), "target-lang-slug", "target-lang.pdf"),
        )
        document_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Body', 'Argon plasma text', 'body')
            """,
            (document_id,),
        )

    result = translation_service.translate_document(document_id, "zh/CN")

    assert result["status"] == "done"
    assert result["target_lang"] == "zh/CN"
    output_path = Path(result["output_path"])
    assert output_path.name == f"document-{document_id}-zh-CN.md"
    assert output_path.exists()


def test_index_unparsed_document_records_failed_status(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("unindexed.pdf", pdf_bytes(b"Needs parsing before indexing."), "application/pdf")},
    )
    document_id = response.json()["id"]

    accepted = client.post(f"/api/v1/documents/{document_id}/index")
    assert accepted.status_code == 202
    chunks = client.get(f"/api/v1/documents/{document_id}/chunks").json()
    assert chunks["indexed"] is False
    assert chunks["index_status"] == "failed"
    assert "no parsed sections" in chunks["index_error"]


def test_extract_chemistry_unparsed_document_records_failed_status(tmp_path):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("unextracted.pdf", pdf_bytes(b"Needs parsing before extraction."), "application/pdf")},
    )
    document_id = response.json()["id"]

    accepted = client.post(f"/api/v1/documents/{document_id}/extract-chemistry")
    assert accepted.status_code == 202
    document = client.get(f"/api/v1/documents/{document_id}").json()
    assert document["chemistry_status"] == "failed"
    assert "no parsed sections" in document["chemistry_error"]


def test_streamlit_documents_tab_exposes_preview_and_index_status():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]
    for required in [
        "/chunks",
        "translation_preview",
        "index_status",
        "index_error",
        "chemistry_status",
        "chemistry_error",
        "section_preview",
        "parse_error",
        "vector_id",
    ]:
        assert required in documents_section
    assert 'type=["pdf"]' in documents_section
    assert 'type=["pdf", "txt"]' not in documents_section


def test_streamlit_documents_tab_offers_tei_xml_download():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]

    for required in [
        'document_detail.get("tei_path")',
        'tei_path = Path(document_detail.get("tei_path"))',
        "tei_path.exists()",
        "下载 TEI XML",
        "TEI 文件不存在",
    ]:
        assert required in documents_section


def test_streamlit_documents_tab_offers_original_pdf_download():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]

    for required in [
        'document_detail.get("file_path")',
        'pdf_path = Path(document_detail.get("file_path"))',
        "pdf_path.exists()",
        "下载原始 PDF",
        "PDF 文件不存在",
    ]:
        assert required in documents_section


def test_streamlit_documents_tab_exposes_section_and_chunk_pagination_controls():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]

    for required in [
        'sections_page = sections_page_col.number_input("sections_page"',
        "sections_page_size = sections_page_size_col.number_input(",
        '"sections_page_size"',
        "sections_response = api_get(",
        "page=int(sections_page)",
        "page_size=int(sections_page_size)",
        'sections = sections_response["items"]',
        "sections_response['page']",
        "sections_response['page_size']",
        "sections_response['total']",
        'chunks_page = chunks_page_col.number_input("chunks_page"',
        "chunks_page_size = chunks_page_size_col.number_input(",
        '"chunks_page_size"',
        "chunks = api_get(",
        "page=int(chunks_page)",
        "page_size=int(chunks_page_size)",
        "chunks['page']",
        "chunks['page_size']",
        "chunks['total']",
    ]:
        assert required in documents_section


def test_streamlit_document_parse_surfaces_success_and_error_states():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]

    for required in [
        'status_code, parse_payload = api_post(f"/documents/{selected[\'id\']}/parse")',
        "if status_code < 400:",
        "已创建解析任务",
        "else:",
        "st.warning(parse_payload)",
        "st.json(parse_payload)",
    ]:
        assert required in documents_section


def test_streamlit_document_translate_surfaces_success_and_error_states():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]

    for required in [
        "translation_target_lang",
        'key=f"translation-target-lang-{selected[\'id\']}"',
        'json={"target_lang": translation_target_lang}',
        "if status_code < 400:",
        "已创建翻译任务",
        "else:",
        "st.warning(translate_payload)",
        "st.json(translate_payload)",
    ]:
        assert required in documents_section


def test_streamlit_document_index_surfaces_success_and_error_states():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]

    for required in [
        'status_code, index_payload = api_post(f"/documents/{selected[\'id\']}/index")',
        "if status_code < 400:",
        "已创建索引任务",
        "else:",
        "st.warning(index_payload)",
        "st.json(index_payload)",
    ]:
        assert required in documents_section


def test_streamlit_document_extract_surfaces_success_and_error_states():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]

    for required in [
        'status_code, extract_payload = api_post(f"/documents/{selected[\'id\']}/extract-chemistry")',
        "if status_code < 400:",
        "已创建化学抽取任务",
        "else:",
        "st.warning(extract_payload)",
        "st.json(extract_payload)",
    ]:
        assert required in documents_section


def test_streamlit_documents_tab_shows_linked_paper_summary():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]

    for required in [
        'linked_paper = document_detail.get("paper")',
        "关联论文",
        'linked_paper.get("title")',
        'linked_paper.get("doi")',
        'linked_paper.get("journal_name")',
        'linked_paper.get("published_date")',
    ]:
        assert required in documents_section


def test_streamlit_translation_preview_shows_failed_status():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]
    translation_section = documents_section[
        documents_section.index("with translation_tab:") : documents_section.index("with chunks_tab:")
    ]

    for required in [
        'translation_preview.get("status") == "failed"',
        'translation_preview.get("error")',
        "translation failed",
        'translation_preview.get("output_path")',
    ]:
        assert required in translation_section


def test_streamlit_translation_preview_offers_download():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]
    translation_section = documents_section[
        documents_section.index("with translation_tab:") : documents_section.index("with chunks_tab:")
    ]

    for required in [
        "translation_text",
        "st.download_button",
        "下载双语翻译",
        'mime="text/markdown"',
        "file_name=output_path.name",
    ]:
        assert required in translation_section


def test_streamlit_translation_preview_warns_when_output_file_is_missing():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]
    translation_section = documents_section[
        documents_section.index("with translation_tab:") : documents_section.index("with chunks_tab:")
    ]

    for required in [
        'output_path = Path(translation_preview.get("output_path"))',
        "output_path.exists()",
        "翻译文件不存在",
    ]:
        assert required in translation_section


def test_streamlit_rag_tab_separates_answer_and_sources():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    rag_section = streamlit[streamlit.index("with rag_tab:") : streamlit.index("with chemistry_tab:")]

    for required in [
        "rag_payload",
        'rag_payload.get("answer")',
        'rag_payload.get("sources")',
        "引用来源",
        "st.dataframe(sources",
        "paper_id",
        "paper_title",
        "source_excerpt",
        'source_preview.get("source_excerpt")',
        "st.code(source_preview.get(\"source_excerpt\")",
        "chunk_id",
        "section_title",
    ]:
        assert required in rag_section


def test_streamlit_rag_tab_validates_document_ids_before_query():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    rag_section = streamlit[streamlit.index("with rag_tab:") : streamlit.index("with chemistry_tab:")]

    for required in [
        "document_id_error",
        "document_ids 只能包含整数",
        "try:",
        "except ValueError",
        "if document_id_error:",
        "else:",
        "api_post(",
        '"/rag/query"',
    ]:
        assert required in rag_section


def test_streamlit_rag_tab_exposes_top_k_control():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    rag_section = streamlit[streamlit.index("with rag_tab:") : streamlit.index("with chemistry_tab:")]

    for required in [
        'top_k = st.number_input("top_k"',
        "min_value=1",
        "max_value=20",
        "value=6",
        '"top_k": int(top_k)',
    ]:
        assert required in rag_section


def test_streamlit_rag_tab_can_select_documents_for_query_scope():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    rag_section = streamlit[streamlit.index("with rag_tab:") : streamlit.index("with chemistry_tab:")]

    for required in [
        'rag_documents = rag_documents_response["items"]',
        "selected_rag_documents = st.multiselect(",
        "限定文档",
        "selected_document_ids",
        "ids = list(dict.fromkeys(selected_document_ids + typed_document_ids))",
        "暂无可选文档",
    ]:
        assert required in rag_section


def test_streamlit_rag_tab_exposes_document_pagination_controls():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    rag_section = streamlit[streamlit.index("with rag_tab:") : streamlit.index("with chemistry_tab:")]

    for required in [
        'rag_documents_page = rag_documents_page_col.number_input("rag_documents_page"',
        "rag_documents_page_size = rag_documents_page_size_col.number_input(",
        '"rag_documents_page_size"',
        'rag_documents_response = api_get("/documents", page=int(rag_documents_page), page_size=int(rag_documents_page_size))',
        'rag_documents = rag_documents_response["items"]',
        "rag_documents_response['page']",
        "rag_documents_response['page_size']",
        "rag_documents_response['total']",
    ]:
        assert required in rag_section


def test_streamlit_document_upload_shows_duplicate_result():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]

    for required in [
        '"document_duplicate"',
        'payload.get("document")',
        "已有文档",
        "duplicate_document",
    ]:
        assert required in documents_section


def test_streamlit_documents_tab_shows_empty_state():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]

    assert "暂无文档，请先上传 PDF。" in documents_section


def test_streamlit_documents_tab_exposes_pagination_controls():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    documents_section = streamlit[streamlit.index("with documents_tab:") : streamlit.index("with rag_tab:")]

    for required in [
        'documents_page = documents_page_col.number_input("documents_page"',
        "documents_page_size = documents_page_size_col.number_input(",
        '"documents_page_size"',
        'documents_response = api_get("/documents", page=int(documents_page), page_size=int(documents_page_size))',
        'docs = documents_response["items"]',
        "documents_response['page']",
        "documents_response['page_size']",
        "documents_response['total']",
    ]:
        assert required in documents_section


def test_streamlit_sidebar_exposes_runtime_status():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    sidebar_section = streamlit[streamlit.index("with st.sidebar:") : streamlit.index("with search_tab:")]

    for required in ["runtime", "scheduler_enabled", "scheduler_jobs", "api_prefix", "version"]:
        assert required in sidebar_section


def test_streamlit_sidebar_exposes_external_capability_status():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    sidebar_section = streamlit[streamlit.index("with st.sidebar:") : streamlit.index("with search_tab:")]

    for required in [
        "外部能力",
        "external_capabilities",
        "openalex_mailto",
        "unpaywall_email",
        "grobid_url",
        "llm_api_key",
        "embedding_model",
        "vector_db_backend",
    ]:
        assert required in sidebar_section


def test_streamlit_sidebar_surfaces_config_warnings():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    sidebar_section = streamlit[streamlit.index("with st.sidebar:") : streamlit.index("with search_tab:")]

    for required in ["config_warnings", "capability", "message"]:
        assert required in sidebar_section


def test_streamlit_sidebar_surfaces_storage_health():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    sidebar_section = streamlit[streamlit.index("with st.sidebar:") : streamlit.index("with search_tab:")]

    for required in [
        "存储健康",
        "storage_health",
        "data_dir",
        "pdf_dir",
        "tei_dir",
        "translation_dir",
        "export_dir",
        "database",
        "vector_db",
        "writable",
        "valid_json",
    ]:
        assert required in sidebar_section


def test_streamlit_sidebar_surfaces_workflow_status_counts():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    sidebar_section = streamlit[streamlit.index("with st.sidebar:") : streamlit.index("with search_tab:")]

    for required in [
        "状态分布",
        "status_counts",
        "crawl_jobs",
        "document_parse",
        "document_index",
        "document_chemistry",
        "translations",
        "reaction_sets",
        "status_count_rows",
        "st.dataframe(status_count_rows",
    ]:
        assert required in sidebar_section


def test_streamlit_sidebar_can_check_grobid_live_status():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    sidebar_section = streamlit[streamlit.index("with st.sidebar:") : streamlit.index("with search_tab:")]

    for required in [
        "检查 GROBID",
        'api_get("/system/status", check_external=True)',
        "grobid = external_capabilities.get(\"grobid\") or {}",
        "GROBID live",
        "status_code",
        "error",
        "未检查",
        "可用",
        "不可用",
    ]:
        assert required in sidebar_section


def test_streamlit_crawl_jobs_table_flattens_diagnostics():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    flatten_helper = streamlit[streamlit.index("def flatten_crawl_job_rows") : streamlit.index("st.set_page_config")]
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("with config_tab:")]

    for required in [
        "diagnostics",
        "journal",
        "papers_found",
        "papers_filtered",
        "papers_accepted",
        "papers_existing",
        "papers_new",
    ]:
        assert required in flatten_helper
    assert "flatten_crawl_job_rows(jobs)" in search_section
    assert 'st.dataframe(flatten_crawl_job_rows(jobs), use_container_width=True)' in search_section


def test_streamlit_crawl_jobs_show_empty_state():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("with config_tab:")]

    assert "暂无抓取任务。" in search_section


def test_streamlit_crawl_jobs_exposes_pagination_controls():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("with config_tab:")]

    for required in [
        'crawl_jobs_page = crawl_jobs_page_col.number_input("crawl_jobs_page"',
        "crawl_jobs_page_size = crawl_jobs_page_size_col.number_input(",
        '"crawl_jobs_page_size"',
        'crawl_jobs_response = api_get("/crawl/jobs", page=int(crawl_jobs_page), page_size=int(crawl_jobs_page_size))',
        'jobs = crawl_jobs_response["items"]',
        "crawl_jobs_response['page']",
        "crawl_jobs_response['page_size']",
        "crawl_jobs_response['total']",
    ]:
        assert required in search_section


def test_streamlit_crawl_run_surfaces_success_and_error_states():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("with config_tab:")]

    for required in [
        'status_code, crawl_payload = api_post("/crawl/run", json=body)',
        "if status_code < 400:",
        "已创建抓取任务",
        "else:",
        "st.warning(crawl_payload)",
        "st.json(crawl_payload)",
    ]:
        assert required in search_section


def test_streamlit_search_results_show_dedupe_strategy():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("st.divider()", streamlit.index("with search_tab:"))]

    assert "dedupe_strategy" in search_section
    assert "dedupe_strategy=" in search_section


def test_streamlit_search_tab_exposes_sort_control():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("st.divider()", streamlit.index("with search_tab:"))]

    for required in [
        'sort_choice = col7.selectbox("排序", ["date_desc", "relevance"])',
        '"sort": sort_choice',
    ]:
        assert required in search_section


def test_streamlit_search_results_can_trigger_classification():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("st.divider()", streamlit.index("with search_tab:"))]

    for required in [
        "分类结果",
        "触发分类",
        'api_post(f"/papers/{paper[\'id\']}/classify")',
        "format_category_summary(classified_paper)",
        'key=f"classify-paper-{paper[\'id\']}"',
    ]:
        assert required in search_section


def test_streamlit_search_results_can_override_categories_manually():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("st.divider()", streamlit.index("with search_tab:"))]

    for required in [
        "人工覆盖分类",
        "保存人工分类",
        "selected_category_ids",
        "api_put(",
        'f"/papers/{paper[\'id\']}/categories"',
        '"method": "manual"',
        'key=f"manual-categories-{paper[\'id\']}"',
        'key=f"save-manual-categories-{paper[\'id\']}"',
    ]:
        assert required in search_section


def test_streamlit_search_results_can_resolve_oa_manually():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("st.divider()", streamlit.index("with search_tab:"))]

    for required in [
        "重新解析 OA",
        'api_post(f"/papers/{paper[\'id\']}/resolve-oa")',
        'resolved_paper.get("oa_status")',
        'resolved_paper.get("oa_pdf_url")',
        'key=f"resolve-oa-{paper[\'id\']}"',
    ]:
        assert required in search_section


def test_streamlit_search_tab_handles_empty_results_and_api_errors():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("st.divider()", streamlit.index("with search_tab:"))]

    for required in [
        "search_error",
        "检索失败",
        "没有检索结果",
        "sort=relevance requires q",
        'elif sort_choice == "relevance" and not q.strip():',
        "try:",
        'papers = {"items": [], "total": 0, "page": 1, "page_size": 20}',
        'if not search_error and papers["total"] == 0:',
    ]:
        assert required in search_section


def test_streamlit_search_tab_exposes_year_filters():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("st.divider()", streamlit.index("with search_tab:"))]

    for required in [
        'number_input("year_from"',
        'number_input("year_to"',
        'params["year_from"]',
        'params["year_to"]',
    ]:
        assert required in search_section


def test_streamlit_search_tab_exposes_pagination_controls():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("st.divider()", streamlit.index("with search_tab:"))]

    for required in [
        "search_page",
        "search_page_size",
        '"page": int(search_page)',
        '"page_size": int(search_page_size)',
        'st.caption(f"page {papers[\'page\']} · page_size {papers[\'page_size\']}")',
    ]:
        assert required in search_section


def test_streamlit_api_put_preserves_json_errors_for_callers():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    api_put_section = streamlit[streamlit.index("def api_put") : streamlit.index("st.set_page_config")]

    assert "response.raise_for_status()" not in api_put_section
    assert 'return request_json_status("PUT", API_BASE, path, json=json, timeout=20)' in api_put_section
    assert "response.json()" not in api_put_section

    journals_section = streamlit[streamlit.index("更新期刊") : streamlit.index("st.divider()", streamlit.index("更新期刊"))]
    assert "status_code, result = api_put(" in journals_section
    assert "if status_code < 400:" in journals_section
    assert "st.warning(result)" in journals_section

    reactions_section = streamlit[streamlit.index("with chemistry_tab:") :]
    assert "status_code, result = api_put(" in reactions_section
    assert "st.session_state[\"reaction_set_detail\"] = result" in reactions_section
    assert "st.warning(result)" in reactions_section


def test_streamlit_config_tab_exposes_journal_and_category_management():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    helper_section = streamlit[: streamlit.index("def flatten_crawl_job_rows")]
    assert "配置" in streamlit
    config_section = streamlit[streamlit.index("with config_tab:") :]
    assert "def api_delete(path: str):" in helper_section
    for required in [
        "/journals",
        "/categories",
        "新增期刊",
        "更新期刊",
        "停用期刊",
        "新增分类",
        "keywords_mode",
        "keywords_terms",
        "active",
        "api_post(\"/journals\"",
        "f\"/journals/{selected_journal['id']}\"",
        "api_delete(f\"/journals/{selected_journal['id']}\")",
        "api_post(\"/categories\"",
    ]:
        assert required in config_section


def test_streamlit_config_tab_normalizes_journal_keywords_for_dataframe():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    config_section = streamlit[streamlit.index("with config_tab:") : streamlit.index("with documents_tab:")]

    for required in [
        "journals_table",
        'json.dumps(journal.get("keywords"), ensure_ascii=False)',
        "st.dataframe(journals_table, use_container_width=True)",
    ]:
        assert required in config_section


def test_streamlit_config_tab_exposes_journal_pagination_controls():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    config_section = streamlit[streamlit.index("with config_tab:") : streamlit.index("with documents_tab:")]

    for required in [
        "config_journals_page = config_journals_page_col.number_input(",
        '"config_journals_page"',
        "config_journals_page_size = config_journals_page_size_col.number_input(",
        '"config_journals_page_size"',
        'journals_response = api_get("/journals", page=int(config_journals_page), page_size=int(config_journals_page_size))',
        "journals_response['page']",
        "journals_response['page_size']",
        "journals_response['total']",
    ]:
        assert required in config_section


def test_streamlit_config_tab_can_update_journal_year_range():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    journals_section = streamlit[streamlit.index("更新期刊") : streamlit.index("停用期刊")]

    for required in [
        "edit_year_from",
        "edit_year_to",
        'selected_journal.get("year_from")',
        'selected_journal.get("year_to")',
        '"year_from": int(edit_year_from)',
        '"year_to": int(edit_year_to) if edit_year_to else None',
        "year_from must be less than or equal to year_to",
    ]:
        assert required in journals_section


def test_streamlit_config_tab_can_create_journal_with_year_to():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    create_section = streamlit[streamlit.index('with st.form("create-journal-form")') : streamlit.index("if journals_all:")]

    for required in [
        "new_journal_year_to",
        'key="new-journal-year-to"',
        '"year_to": int(new_journal_year_to) if new_journal_year_to else None',
        "year_from must be less than or equal to year_to",
    ]:
        assert required in create_section
