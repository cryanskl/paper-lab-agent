import hashlib
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.config import get_settings
from app.db import get_conn
from app.services.documents import assert_safe_document_storage_path, count_pdf_pages
from app.services.rag import get_vector_store
from app.utils import json_dumps


FIXTURE_PAPERS = [
    {
        "doi": "10.1088/1361-6595/fixture-ar-o2",
        "title": "Global model of an Ar/O2 inductively coupled plasma",
        "abstract": "A fixture paper about low temperature plasma chemistry, reaction kinetics, and plasma simulation.",
        "journal_id": 2,
        "journal_name": "Plasma Sources Science and Technology",
        "published_date": "2026-01-15",
        "published_year": 2026,
        "landing_url": "https://example.test/papers/ar-o2-icp",
        "oa_status": "green",
        "oa_pdf_url": "https://example.test/papers/ar-o2-icp.pdf",
        "source_api": "fixture",
    },
    {
        "doi": "10.1063/fixture-ccp-sheath",
        "title": "Sheath dynamics in capacitively coupled plasma simulations",
        "abstract": "A fixture paper about sheath physics, diagnostics, and low temperature plasma methods.",
        "journal_id": 1,
        "journal_name": "Physics of Plasmas",
        "published_date": "2025-11-02",
        "published_year": 2025,
        "landing_url": "https://example.test/papers/ccp-sheath",
        "oa_status": "unknown",
        "oa_pdf_url": None,
        "source_api": "fixture",
    },
]

def build_fixture_pdf() -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(
        buffer,
        pagesize=letter,
        pageCompression=1,
        invariant=1,
    )
    width, height = letter
    pdf.setTitle("Global model of an Ar/O2 inductively coupled plasma")
    pdf.setAuthor("Paper Lab Fixture Authors")
    pdf.setSubject("Deterministic fixture for GROBID integration tests")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(54, height - 58, "Global model of an Ar/O2 inductively coupled plasma")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(54, height - 78, "Paper Lab Fixture Authors")

    text = pdf.beginText(54, height - 112)
    text.setLeading(15)
    article_lines = [
        ("Helvetica-Bold", 12, "Abstract"),
        (
            "Helvetica",
            10,
            "This deterministic fixture describes low-temperature Ar/O2 plasma chemistry,",
        ),
        (
            "Helvetica",
            10,
            "electron-impact ionization, reaction kinetics, and global plasma simulation.",
        ),
        ("Helvetica-Bold", 12, "1. Introduction"),
        (
            "Helvetica",
            10,
            "Inductively coupled plasmas are widely used to study reactive gas mixtures.",
        ),
        (
            "Helvetica",
            10,
            "This fixture provides searchable text and article-like structure for PDF parsing.",
        ),
        ("Helvetica-Bold", 12, "2. Reaction chemistry"),
        ("Courier", 10, "e + Ar -> e + e + Ar+"),
        (
            "Helvetica",
            10,
            "The ionization reaction is e + Ar -> e + e + Ar+ .",
        ),
        (
            "Helvetica",
            10,
            "The rate coefficient is reported as k_1 without automatic unit conversion.",
        ),
        (
            "Helvetica",
            10,
            "Cross-section source: LXCat IST-Lisbon, https://nl.lxcat.net/data/set/example",
        ),
        ("Helvetica-Bold", 12, "3. Conclusion"),
        (
            "Helvetica",
            10,
            "The document is intentionally short but is a standards-compliant PDF.",
        ),
        ("Helvetica-Bold", 12, "References"),
        (
            "Helvetica",
            10,
            "[1] Paper Lab Fixture Authors, Plasma Sources Science and Technology, 2026.",
        ),
    ]
    for font_name, font_size, line in article_lines:
        text.setFont(font_name, font_size)
        text.textLine(line)
    pdf.drawText(text)
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(width / 2, 30, "Paper Lab deterministic GROBID fixture - page 1")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


FIXTURE_DOCUMENTS = [
    {
        "paper_doi": "10.1088/1361-6595/fixture-ar-o2",
        "original_name": "fixture-plasma-chemistry.pdf",
        "content": build_fixture_pdf(),
    }
]


def load_fixture_papers() -> dict:
    inserted = 0
    updated = 0
    with get_conn() as conn:
        for paper in FIXTURE_PAPERS:
            existing = conn.execute("SELECT id FROM papers WHERE doi=?", (paper["doi"],)).fetchone()
            params = (
                paper["doi"],
                paper["title"],
                paper["abstract"],
                json_dumps([]),
                paper["journal_id"],
                paper["journal_name"],
                paper["published_date"],
                paper["published_year"],
                paper["landing_url"],
                paper["oa_status"],
                paper["oa_pdf_url"],
                paper["source_api"],
                json_dumps({"fixture": True}),
            )
            if existing:
                conn.execute(
                    """
                    UPDATE papers SET title=?, abstract=?, authors=?, journal_id=?, journal_name=?,
                        published_date=?, published_year=?, landing_url=?, oa_status=?, oa_pdf_url=?,
                        source_api=?, raw_metadata=?, updated_at=datetime('now')
                    WHERE doi=?
                    """,
                    params[1:] + (paper["doi"],),
                )
                updated += 1
            else:
                conn.execute(
                    """
                    INSERT INTO papers (
                        doi, title, abstract, authors, journal_id, journal_name, published_date,
                        published_year, landing_url, oa_status, oa_pdf_url, source_api, raw_metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    params,
                )
                inserted += 1
    return {"inserted": inserted, "updated": updated}


def load_fixture_documents() -> dict:
    settings = get_settings()
    inserted = 0
    updated = 0
    with get_conn() as conn:
        for document in FIXTURE_DOCUMENTS:
            content = document["content"]
            digest = hashlib.sha256(content).hexdigest()
            stored = settings.pdf_dir / f"{digest}.pdf"
            assert_safe_document_storage_path(stored)
            stored.write_bytes(content)
            paper = conn.execute("SELECT id FROM papers WHERE doi=?", (document["paper_doi"],)).fetchone()
            paper_id = paper["id"] if paper else None
            existing = conn.execute(
                "SELECT id, file_hash FROM documents WHERE file_hash=?",
                (digest,),
            ).fetchone()
            if existing is None and paper_id is not None:
                existing = conn.execute(
                    """
                    SELECT id, file_hash
                    FROM documents
                    WHERE paper_id=? AND original_name=?
                    ORDER BY id
                    LIMIT 1
                    """,
                    (paper_id, document["original_name"]),
                ).fetchone()
            params = (
                paper_id,
                str(stored),
                digest,
                document["original_name"],
                count_pdf_pages(content),
            )
            if existing:
                document_id = int(existing["id"])
                if existing["file_hash"] != digest:
                    get_vector_store(settings).delete_document(document_id)
                    conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
                    conn.execute("DELETE FROM translations WHERE document_id=?", (document_id,))
                    conn.execute("DELETE FROM reaction_sets WHERE document_id=?", (document_id,))
                    conn.execute("DELETE FROM sections WHERE document_id=?", (document_id,))
                    conn.execute(
                        """
                        UPDATE documents
                        SET paper_id=?,
                            file_path=?,
                            file_hash=?,
                            original_name=?,
                            num_pages=?,
                            parse_status='uploaded',
                            parse_error=NULL,
                            index_status='not_indexed',
                            index_error=NULL,
                            chemistry_status='not_extracted',
                            chemistry_error=NULL,
                            tei_path=NULL
                        WHERE id=?
                        """,
                        params + (document_id,),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE documents
                        SET paper_id=?, file_path=?, original_name=?, num_pages=?
                        WHERE id=?
                        """,
                        (
                            paper_id,
                            str(stored),
                            document["original_name"],
                            count_pdf_pages(content),
                            document_id,
                        ),
                    )
                updated += 1
            else:
                conn.execute(
                    """
                    INSERT INTO documents (paper_id, file_path, file_hash, original_name, num_pages, parse_status)
                    VALUES (?, ?, ?, ?, ?, 'uploaded')
                    """,
                    params,
                )
                inserted += 1
    return {"inserted": inserted, "updated": updated}
