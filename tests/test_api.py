import os
from pathlib import Path


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


def test_document_rag_chemistry_export_gate(tmp_path):
    client = make_client(tmp_path)
    content = b"This section describes plasma chemistry. e + Ar -> e + e + Ar+ . The rate is $k_1$ ."
    response = client.post(
        "/api/v1/documents",
        files={"file": ("sample.pdf", content, "application/pdf")},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    assert client.post(f"/api/v1/documents/{document_id}/parse").status_code == 202
    sections = client.get(f"/api/v1/documents/{document_id}/sections").json()["items"]
    assert sections

    assert client.post(f"/api/v1/documents/{document_id}/translate", json={"target_lang": "zh"}).status_code == 202
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

