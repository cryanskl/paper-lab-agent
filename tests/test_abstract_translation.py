import os


def make_client(tmp_path):
    os.environ["DATABASE_PATH"] = str(tmp_path / "test.db")
    os.environ["PAPER_LAB_DATA_DIR"] = str(tmp_path)
    os.environ["PAPER_LAB_TRANSLATION_DIR"] = str(tmp_path / "translations")

    from app.config import get_settings
    from app.db import init_db
    from app.main import app
    from fastapi.testclient import TestClient

    get_settings.cache_clear()
    init_db()
    return TestClient(app)


class ChineseTranslator:
    def translate(self, text, target_lang):
        return f"中文译文：N<sub>e</sub> &amp; {text}"


def seed_paper(abstract):
    from app.db import get_conn

    with get_conn() as conn:
        return conn.execute(
            """
            INSERT INTO papers (title, abstract, authors, raw_metadata)
            VALUES ('Metadata abstract paper', ?, '[]', '{}')
            """,
            (abstract,),
        ).lastrowid


def test_paper_abstract_translation_uses_metadata_without_document(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    from app.services import translation as translation_service

    monkeypatch.setattr(
        translation_service,
        "get_translator",
        lambda settings: ChineseTranslator(),
    )
    paper_id = seed_paper("Downloaded metadata abstract.")

    accepted = client.post(
        f"/api/v1/papers/{paper_id}/abstract-translation",
        json={"target_lang": "zh"},
    )

    assert accepted.status_code == 202
    assert accepted.json()["paper_id"] == paper_id
    result = client.get(
        f"/api/v1/papers/{paper_id}/abstract-translation",
        params={"target_lang": "zh"},
    )
    assert result.status_code == 200
    payload = result.json()
    assert payload["status"] == "done"
    assert payload["source_text"] == "Downloaded metadata abstract."
    assert payload["target_text"] == "中文译文：Ne & Downloaded metadata abstract."


def test_paper_abstract_translation_reuses_matching_cached_source(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    from app.services import translation as translation_service

    monkeypatch.setattr(
        translation_service,
        "get_translator",
        lambda settings: ChineseTranslator(),
    )
    paper_id = seed_paper("Stable abstract.")

    first = client.post(
        f"/api/v1/papers/{paper_id}/abstract-translation",
        json={"target_lang": "zh"},
    ).json()
    second = client.post(
        f"/api/v1/papers/{paper_id}/abstract-translation",
        json={"target_lang": "zh"},
    ).json()

    assert second["job_id"] == first["job_id"]
    assert second["status"] == "done"


def test_paper_abstract_translation_rejects_missing_abstract(tmp_path):
    client = make_client(tmp_path)
    paper_id = seed_paper(None)

    response = client.post(
        f"/api/v1/papers/{paper_id}/abstract-translation",
        json={"target_lang": "zh"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "paper_abstract_missing",
            "message": "Paper metadata has no abstract",
        }
    }
