import os
from pathlib import Path


def pdf_bytes(content: bytes) -> bytes:
    return b"%PDF-1.4\n" + content


def health_check_counts(**overrides):
    counts = {
        "journals": 6,
        "papers": 1,
        "categories": 7,
        "crawl_jobs": 0,
        "documents": 0,
        "sections": 0,
        "translations": 0,
        "chunks": 0,
        "reaction_sets": 0,
        "reactions": 0,
    }
    counts.update(overrides)
    return counts


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
    with get_conn() as conn:
        row = conn.execute(
            "SELECT confidence, method FROM paper_categories WHERE paper_id=? AND category_id=2",
            (paper_id,),
        ).fetchone()
    assert row["confidence"] == 0.91
    assert row["method"] == "auto"


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


def test_papers_reject_unknown_sort(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/v1/papers", params={"sort": "title_asc"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


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


def test_create_category_with_unknown_parent_returns_json_error(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/categories",
        json={"name": "Unknown Parent Child", "slug": "unknown-parent-child", "parent_id": 9999},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "category_parent_not_found"


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


def test_fixture_import_script_runs_from_repo_root(tmp_path):
    import subprocess
    import sys

    env = os.environ.copy()
    env["DATABASE_PATH"] = str(tmp_path / "script.db")
    env["PAPER_LAB_DATA_DIR"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "scripts/import_fixtures.py"],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "inserted" in result.stdout


def test_smoke_check_covers_translation_and_chemistry_chain():
    from scripts.smoke_check import run_smoke

    result = run_smoke()

    assert result["translation_status"] == "done"
    assert result["reaction_sets"] == 1
    assert result["reactions"] == 1
    assert result["blocked_export_status"] == 409
    assert result["verified_export_format"] == "json"
    assert result["translation_output_path"].endswith("document-1-zh.md")
    assert result["verified_export_path"].endswith("reaction-set-1.json")


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


def test_resolve_oa_passes_unpaywall_retry_and_timeout_settings(tmp_path, monkeypatch):
    client = make_client(tmp_path)

    from app.config import get_settings
    from app.db import get_conn
    from app.routers import papers as papers_router

    get_settings.cache_clear()
    monkeypatch.setenv("UNPAYWALL_API_MAX_RETRIES", "6")
    monkeypatch.setenv("UNPAYWALL_API_RETRY_BACKOFF_SECONDS", "0")
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
            {"max_retries": 6, "retry_backoff_seconds": 0.0, "timeout": 11.0},
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


def test_crawl_job_passes_api_retry_and_page_settings(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.config import get_settings
    from app.services import crawl as crawl_service

    get_settings.cache_clear()
    monkeypatch.setenv("ACADEMIC_API_MAX_PAGES", "4")
    monkeypatch.setenv("ACADEMIC_API_MAX_RETRIES", "5")
    monkeypatch.setenv("ACADEMIC_API_RETRY_BACKOFF_SECONDS", "0")
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
            {"max_retries": 5, "retry_backoff_seconds": 0.0, "timeout": 7.0},
        ),
        (
            "crossref",
            None,
            {"max_retries": 5, "retry_backoff_seconds": 0.0, "timeout": 7.0},
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


def test_crawl_job_passes_unpaywall_retry_and_timeout_settings(tmp_path, monkeypatch):
    make_client(tmp_path)

    from app.config import get_settings
    from app.services import crawl as crawl_service

    get_settings.cache_clear()
    monkeypatch.setenv("UNPAYWALL_API_MAX_RETRIES", "4")
    monkeypatch.setenv("UNPAYWALL_API_RETRY_BACKOFF_SECONDS", "0")
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
            {"max_retries": 4, "retry_backoff_seconds": 0.0, "timeout": 9.0},
        )
    ]


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


def test_parse_document_records_grobid_fallback_reason(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("sample.pdf", pdf_bytes(b"local plasma text"), "application/pdf")},
    )
    document_id = response.json()["id"]

    from app.services import documents as document_service

    async def fake_health(self):
        return False

    monkeypatch.setattr(document_service.GrobidClient, "health", fake_health)

    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    document = client.get(f"/api/v1/documents/{document_id}").json()
    assert document["parse_status"] == "parsed"
    assert "GROBID is unavailable" in document["parse_error"]


def test_parse_document_fallback_writes_valid_tei_xml(tmp_path, monkeypatch):
    import xml.etree.ElementTree as ET

    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("xml-fallback.pdf", pdf_bytes(b"Ar & O2 <plasma> chemistry"), "application/pdf")},
    )
    document_id = response.json()["id"]

    from app.services import documents as document_service

    async def fake_health(self):
        return False

    monkeypatch.setattr(document_service.GrobidClient, "health", fake_health)

    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    document = client.get(f"/api/v1/documents/{document_id}").json()
    tei_text = Path(document["tei_path"]).read_text(encoding="utf-8")

    ET.fromstring(tei_text)
    assert "Ar &amp; O2 &lt;plasma&gt; chemistry" in tei_text


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
    assert "translated::Reaction Rate" not in output
    assert "Smith 2026 Plasma Chemistry" in output
    assert "translated::Smith" not in output


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
                "dimensions": 64,
            }
        }
    )

    result = query("metastable", [document_id], 3)

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
    reaction_id = detail["reactions"][0]["id"]
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
    assert "CROSS_SECTION_URL: https://nl.lxcat.net/data/set/example" in text

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


def test_release_runbook_artifacts_exist_and_document_commands():
    repo = Path(__file__).resolve().parent.parent
    health_check = repo / "scripts" / "health_check.py"
    env_script = repo / "scripts" / "env.sh"
    dev_script = repo / "scripts" / "dev.sh"
    release_check = repo / "scripts" / "release_check.sh"
    smoke_check = repo / "scripts" / "smoke_check.py"
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
    assert "bash -n scripts/env.sh" in release_text
    assert "bash -n scripts/dev.sh" in release_text
    assert (
        "-m py_compile scripts/health_check.py scripts/import_fixtures.py scripts/smoke_check.py streamlit_app.py"
        in release_text
    )
    assert "-m scripts.smoke_check" in release_text
    assert "-m pytest -q" in release_text
    assert smoke_check.exists()
    smoke_text = smoke_check.read_text(encoding="utf-8")
    assert "load_fixture_papers" in smoke_text
    assert '"/api/v1/papers?q=plasma"' in smoke_text
    assert '"/api/v1/system/status"' in smoke_text
    assert ci_workflow.exists()
    ci_text = ci_workflow.read_text(encoding="utf-8")
    assert "bash scripts/release_check.sh" in ci_text
    for required in [
        "bash scripts/dev.sh",
        "python scripts/health_check.py",
        "API_BASE_URL=http://127.0.0.1:8001/api/v1 python scripts/health_check.py",
        "docker run --rm -p 8070:8070 lfoppiano/grobid",
        "`--check-external` 会主动检查 GROBID",
        "python scripts/import_fixtures.py",
        "python -m scripts.smoke_check",
        "bash scripts/release_check.sh",
        "PAPER_LAB_SCHEDULER_ENABLED=true",
        "DEV_READY_TIMEOUT",
        "/_stcore/health",
    ]:
        assert required in readme
    for required in [
        "API_HOST",
        "API_PORT",
        "STREAMLIT_HOST",
        "STREAMLIT_PORT",
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


def test_system_status_contract_documents_operational_counts():
    repo = Path(__file__).resolve().parent.parent
    api_doc = (repo / "docs" / "接口设计文档.md").read_text(encoding="utf-8")
    system_section = api_doc[api_doc.index("## 模块 0") : api_doc.index("## 模块 A")]

    for required in ["categories", "crawl_jobs", "reaction_sets", "reactions"]:
        assert required in system_section


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
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
            },
            "counts": health_check_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 1
    captured = capsys.readouterr()
    assert "runtime" in captured.err


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
            "runtime": {"api_prefix": "/api/v1", "scheduler_enabled": False},
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
            },
            "counts": health_check_counts(),
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
            "runtime": {"api_prefix": "/api/v1", "scheduler_enabled": False},
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": 123,
            },
            "external_capabilities": {
                "openalex_mailto": True,
                "unpaywall_email": True,
                "grobid_url": "http://127.0.0.1:8070",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": False,
                "embedding_model": "local-hash",
            },
            "counts": health_check_counts(),
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
            "runtime": {"api_prefix": "/api/v1", "scheduler_enabled": False},
            "storage": {
                "data_dir": "/tmp/data",
                "pdf_dir": "/tmp/data/pdfs",
                "tei_dir": "/tmp/data/tei",
                "translation_dir": "/tmp/data/translations",
                "export_dir": "/tmp/data/exports",
                "vector_db_path": "/tmp/data/vector-index.json",
            },
            "external_capabilities": {
                "openalex_mailto": "yes",
                "unpaywall_email": True,
                "grobid_url": "",
                "grobid": {"url": "http://127.0.0.1:8070", "available": None, "status_code": None, "error": None},
                "llm_api_key": "false",
                "embedding_model": 123,
            },
            "counts": health_check_counts(),
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
            "runtime": {"api_prefix": "/api/v1", "scheduler_enabled": False},
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
                "grobid": {"url": "", "available": "yes", "status_code": "200", "error": 404},
                "llm_api_key": False,
                "embedding_model": "local-hash",
            },
            "counts": health_check_counts(),
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
            "runtime": {"api_prefix": "/api/v1", "scheduler_enabled": False},
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
            },
            "counts": health_check_counts(journals="6", papers=-1),
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
            "runtime": {"api_prefix": "/api/v1", "scheduler_enabled": False},
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
            },
            "counts": {"journals": 6, "papers": 1, "documents": 0},
        }
    )

    assert "counts missing keys" in "; ".join(errors)
    for required in ["categories", "crawl_jobs", "reaction_sets", "reactions"]:
        assert required in "; ".join(errors)


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
            },
            "counts": health_check_counts(),
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
            },
            "counts": health_check_counts(),
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
            "runtime": {"api_prefix": "/api/v1", "scheduler_enabled": False},
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
            },
            "counts": health_check_counts(),
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
            "runtime": {"api_prefix": "/api/v1", "scheduler_enabled": False},
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
            },
            "counts": health_check_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py", "--base-url", "http://api.test"])

    assert health_check.main() == 0


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

    (tmp_path / ".env").write_text("API_BASE_URL=http://api.test:9001/api/v1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    seen_urls = []

    def fake_fetch_json(url: str, timeout: float) -> dict:
        seen_urls.append(url)
        if url.endswith("/api/v1/health"):
            return {"status": "ok", "service": "paper-lab-agent"}
        return {
            "database_path": "/tmp/plasma.db",
            "runtime": {"api_prefix": "/api/v1", "scheduler_enabled": False},
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
            },
            "counts": health_check_counts(),
        }

    monkeypatch.setattr(health_check, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(sys, "argv", ["health_check.py"])

    assert health_check.main() == 0
    assert seen_urls == [
        "http://api.test:9001/api/v1/health",
        "http://api.test:9001/api/v1/system/status",
    ]


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
            "runtime": {"api_prefix": "/wrong-prefix", "scheduler_enabled": False},
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
            },
            "counts": health_check_counts(),
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
        "未全复核不可导出",
        "未复核",
        "bolsig",
        "format={export_format}",
    ]:
        assert required in chemistry_section


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


def test_document_async_routes_mark_queued_status_before_background_tasks_run(tmp_path):
    from fastapi import BackgroundTasks

    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/documents",
        files={"file": ("queued.pdf", pdf_bytes(b"e + Ar -> e + e + Ar+ ."), "application/pdf")},
    )
    document_id = response.json()["id"]

    from app.routers import documents as document_router

    document_router.parse(document_id, BackgroundTasks())
    document = client.get(f"/api/v1/documents/{document_id}").json()
    assert document["parse_status"] == "parsing"
    assert document["parse_error"] is None

    document_router.translate(document_id, document_router.TranslateIn(target_lang="zh"), BackgroundTasks())
    translation = client.get(f"/api/v1/documents/{document_id}/translation").json()
    assert translation["status"] == "pending"
    assert translation["target_lang"] == "zh"

    document_router.index(document_id, BackgroundTasks())
    chunks = client.get(f"/api/v1/documents/{document_id}/chunks").json()
    assert chunks["index_status"] == "indexing"
    assert chunks["index_error"] is None

    document_router.extract_chemistry(document_id, BackgroundTasks())
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
    assert "e + Ar -> e + e + Ar" in reaction["source_excerpt"]
    assert "Section text before" in reaction["source_excerpt"]
    assert reaction["reactants"] == ["e", "Ar"]
    assert reaction["products"] == ["e", "e", "Ar+"]


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
        "section_preview",
        "parse_error",
        "vector_id",
    ]:
        assert required in documents_section
    assert 'type=["pdf"]' in documents_section
    assert 'type=["pdf", "txt"]' not in documents_section


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


def test_streamlit_sidebar_exposes_runtime_status():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    sidebar_section = streamlit[streamlit.index("with st.sidebar:") : streamlit.index("with search_tab:")]

    for required in ["runtime", "scheduler_enabled", "api_prefix"]:
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


def test_streamlit_search_results_show_dedupe_strategy():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    search_section = streamlit[streamlit.index("with search_tab:") : streamlit.index("st.divider()", streamlit.index("with search_tab:"))]

    assert "dedupe_strategy" in search_section
    assert "dedupe_strategy=" in search_section


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


def test_streamlit_api_put_preserves_json_errors_for_callers():
    repo = Path(__file__).resolve().parent.parent
    streamlit = (repo / "streamlit_app.py").read_text(encoding="utf-8")
    api_put_section = streamlit[streamlit.index("def api_put") : streamlit.index("st.set_page_config")]

    assert "response.raise_for_status()" not in api_put_section
    assert "return response.status_code, response.json()" in api_put_section

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
    assert "配置" in streamlit
    config_section = streamlit[streamlit.index("with config_tab:") :]
    for required in [
        "/journals",
        "/categories",
        "新增期刊",
        "更新期刊",
        "新增分类",
        "keywords_mode",
        "keywords_terms",
        "active",
        "api_post(\"/journals\"",
        "f\"/journals/{selected_journal['id']}\"",
        "api_post(\"/categories\"",
    ]:
        assert required in config_section
