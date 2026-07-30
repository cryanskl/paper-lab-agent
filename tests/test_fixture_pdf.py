import hashlib
import json
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


def configure_test_storage(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("PAPER_LAB_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PAPER_LAB_PDF_DIR", str(tmp_path / "pdfs"))
    monkeypatch.setenv("PAPER_LAB_TEI_DIR", str(tmp_path / "tei"))
    monkeypatch.setenv("PAPER_LAB_TRANSLATION_DIR", str(tmp_path / "translations"))
    monkeypatch.setenv("PAPER_LAB_EXPORT_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("VECTOR_DB_PATH", str(tmp_path / "vector-index.json"))
    monkeypatch.setenv("VECTOR_DB_BACKEND", "local-json")

    from app.config import get_settings
    from app.db import init_db

    get_settings.cache_clear()
    init_db()


def test_fixture_pdf_is_standards_compliant_and_extractable():
    from app.fixture_loader import FIXTURE_DOCUMENTS, build_fixture_pdf

    content = FIXTURE_DOCUMENTS[0]["content"]
    reader = PdfReader(BytesIO(content))

    assert content == build_fixture_pdf()
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert "Global model of an Ar/O2 inductively coupled plasma" in text
    assert "e + Ar -> e + e + Ar+" in text
    assert "%%EOF" in content[-32:].decode("ascii")


def test_fixture_loader_refreshes_legacy_pdf_and_invalidates_derivatives(tmp_path, monkeypatch):
    configure_test_storage(tmp_path, monkeypatch)

    from app.db import get_conn
    from app.fixture_loader import FIXTURE_DOCUMENTS, load_fixture_documents, load_fixture_papers

    load_fixture_papers()
    legacy_content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Page >> endobj\n"
        b"Argon plasma chemistry fixture document.\n"
    )
    legacy_hash = hashlib.sha256(legacy_content).hexdigest()
    legacy_path = tmp_path / "pdfs" / f"{legacy_hash}.pdf"
    legacy_path.write_bytes(legacy_content)

    with get_conn() as conn:
        paper_id = conn.execute(
            "SELECT id FROM papers WHERE doi='10.1088/1361-6595/fixture-ar-o2'"
        ).fetchone()["id"]
        cursor = conn.execute(
            """
            INSERT INTO documents (
                paper_id, file_path, file_hash, original_name, num_pages,
                parse_status, parse_error, index_status, chemistry_status, tei_path
            ) VALUES (?, ?, ?, 'fixture-plasma-chemistry.pdf', 1,
                      'parsed', 'GROBID 500', 'indexed', 'extracted', 'old.tei.xml')
            """,
            (paper_id, str(legacy_path), legacy_hash),
        )
        document_id = int(cursor.lastrowid)
        section_id = int(
            conn.execute(
                """
                INSERT INTO sections (document_id, seq, title, content, section_type)
                VALUES (?, 1, 'Old', 'old text', 'body')
                """,
                (document_id,),
            ).lastrowid
        )
        conn.execute(
            """
            INSERT INTO chunks (document_id, section_id, seq, text, token_count, vector_id, embedded)
            VALUES (?, ?, 1, 'old text', 2, 'fixture-vector', 1)
            """,
            (document_id, section_id),
        )
        conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status)
            VALUES (?, 'en', 'zh', 'done')
            """,
            (document_id,),
        )
        conn.execute(
            """
            INSERT INTO reaction_sets (document_id, name, status)
            VALUES (?, 'Old fixture reactions', 'verified')
            """,
            (document_id,),
        )

    vector_path = tmp_path / "vector-index.json"
    vector_path.write_text(
        json.dumps(
            {
                "fixture-vector": {
                    "chunk_id": 1,
                    "section_id": section_id,
                    "document_id": document_id,
                    "embedding": [1.0],
                    "dimensions": 1,
                    "text": "old text",
                    "embedding_model": "local-hash",
                    "vector_db_backend": "local-json",
                }
            }
        ),
        encoding="utf-8",
    )

    result = load_fixture_documents()

    assert result == {"inserted": 0, "updated": 1}
    with get_conn() as conn:
        document = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
        for table in ("sections", "chunks", "translations", "reaction_sets"):
            assert conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE document_id=?",
                (document_id,),
            ).fetchone()[0] == 0

    expected_content = FIXTURE_DOCUMENTS[0]["content"]
    assert document["file_hash"] == hashlib.sha256(expected_content).hexdigest()
    assert document["parse_status"] == "uploaded"
    assert document["parse_error"] is None
    assert document["index_status"] == "not_indexed"
    assert document["chemistry_status"] == "not_extracted"
    assert document["tei_path"] is None
    assert Path(document["file_path"]).read_bytes() == expected_content
    assert json.loads(vector_path.read_text(encoding="utf-8")) == {}
