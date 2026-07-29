import os
import re
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


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


def seed_translated_document(tmp_path, conn_module, markdown: str) -> int:
    with conn_module.get_conn() as conn:
        document_id = conn.execute(
            "INSERT INTO documents (file_path, parse_status) VALUES ('doc.pdf', 'parsed')"
        ).lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Abstract', 'Argon plasma abstract.', 'abstract')
            """,
            (document_id,),
        )
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 2, 'Table 1', 'rate table', 'table')
            """,
            (document_id,),
        )
        output_path = tmp_path / "translations" / f"document-{document_id}-zh.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status, output_path)
            VALUES (?, 'en', 'zh', 'done', ?)
            """,
            (document_id, str(output_path)),
        )
    return document_id


BILINGUAL_MARKDOWN = """# Bilingual Translation

> Translated with configured model `gpt-4o-mini`.

## Abstract

### Source

Argon plasma abstract.

### zh

氩等离子体摘要。

## Table 1

### Source

rate table

### zh

> Section type `table` is preserved without machine translation.

rate table
"""


def test_parse_translation_markdown_splits_source_and_target_blocks():
    from app.services.translation import parse_translation_markdown

    blocks = parse_translation_markdown(BILINGUAL_MARKDOWN)

    assert [block["title"] for block in blocks] == ["Abstract", "Table 1"]
    assert blocks[0]["source"] == "Argon plasma abstract."
    assert blocks[0]["target"] == "氩等离子体摘要。"
    assert blocks[0]["note"] is None


def test_parse_translation_markdown_keeps_preserved_section_note_out_of_target():
    from app.services.translation import parse_translation_markdown

    blocks = parse_translation_markdown(BILINGUAL_MARKDOWN)

    assert blocks[1]["note"] == "Section type `table` is preserved without machine translation."
    assert blocks[1]["target"] == "rate table"


def test_parse_translation_markdown_returns_empty_list_for_blank_output():
    from app.services.translation import parse_translation_markdown

    assert parse_translation_markdown("") == []


def test_read_translation_markdown_ignores_missing_output_path(tmp_path):
    from app.services.translation import read_translation_markdown

    assert read_translation_markdown(None) == ""
    assert read_translation_markdown(str(tmp_path / "absent.md")) == ""


def test_read_translation_markdown_ignores_symlinked_output(tmp_path):
    from app.services.translation import read_translation_markdown

    real = tmp_path / "real.md"
    real.write_text("## Abstract\n", encoding="utf-8")
    link = tmp_path / "link.md"
    link.symlink_to(real)

    assert read_translation_markdown(str(link)) == ""


def test_translation_sections_align_blocks_with_document_sections(tmp_path):
    client = make_client(tmp_path)
    from app import db
    from app.services.translation import translation_sections

    document_id = seed_translated_document(tmp_path, db, BILINGUAL_MARKDOWN)
    output_path = str(tmp_path / "translations" / f"document-{document_id}-zh.md")

    sections = translation_sections(document_id, output_path)

    assert [section["seq"] for section in sections] == [1, 2]
    assert [section["section_type"] for section in sections] == ["abstract", "table"]
    assert sections[0]["target"] == "氩等离子体摘要。"
    assert sections[0]["section_id"] is not None
    assert client is not None


def test_get_translation_endpoint_returns_reader_sections(tmp_path):
    client = make_client(tmp_path)
    from app import db

    document_id = seed_translated_document(tmp_path, db, BILINGUAL_MARKDOWN)

    response = client.get(f"/api/v1/documents/{document_id}/translation")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "done"
    assert [section["title"] for section in payload["sections"]] == ["Abstract", "Table 1"]
    assert payload["sections"][0]["source"] == "Argon plasma abstract."
    assert payload["sections"][0]["target"] == "氩等离子体摘要。"


def test_get_translation_endpoint_returns_empty_sections_when_output_missing(tmp_path):
    client = make_client(tmp_path)
    from app import db

    with db.get_conn() as conn:
        document_id = conn.execute(
            "INSERT INTO documents (file_path, parse_status) VALUES ('doc.pdf', 'parsed')"
        ).lastrowid
        conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status, error)
            VALUES (?, 'en', 'zh', 'failed', 'document has no parsed sections')
            """,
            (document_id,),
        )

    payload = client.get(f"/api/v1/documents/{document_id}/translation").json()

    assert payload["status"] == "failed"
    assert payload["sections"] == []


def test_root_redirects_to_web_ui(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/ui/"


def test_web_ui_index_and_assets_are_served(tmp_path):
    client = make_client(tmp_path)

    index = client.get("/ui/")
    assert index.status_code == 200
    assert "等离子体文献工作台" in index.text

    for asset in ("/ui/app.js", "/ui/styles.css"):
        assert client.get(asset).status_code == 200


def test_web_ui_health_and_docs_routes_still_resolve(tmp_path):
    client = make_client(tmp_path)

    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/v1/health").json()["status"] == "ok"
    assert client.get("/openapi.json").status_code == 200


def test_web_ui_assets_are_self_contained():
    """The locked stack forbids pulling in a frontend framework or CDN at runtime."""
    sources = "\n".join(
        (WEB_DIR / name).read_text(encoding="utf-8") for name in ("index.html", "app.js", "styles.css")
    )
    remote = re.findall(r"""(?:src|href)=["'](https?://[^"']+)""", sources)

    assert remote == []


def test_web_ui_calls_only_documented_api_prefix():
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "const API = '/api/v1';" in app_js
    assert "fetch(API + path" in app_js
