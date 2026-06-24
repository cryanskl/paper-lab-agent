import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape

from fastapi import UploadFile

from app.clients.grobid import GrobidClient
from app.config import get_settings
from app.db import dict_from_row, get_conn
from app.services.rag import JsonVectorStore
from app.utils import now_iso


def count_pdf_pages(content: bytes) -> Optional[int]:
    matches = re.findall(rb"/Type\s*/Page\b", content)
    return len(matches) or None


def mark_parse_queued(document_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET parse_status='parsing', parse_error=NULL WHERE id=?",
            (document_id,),
        )


async def save_upload(file: UploadFile, paper_id: Optional[int]) -> tuple[dict, bool]:
    settings = get_settings()
    content = await file.read()
    digest = hashlib.sha256(content).hexdigest()
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM documents WHERE file_hash=?", (digest,)).fetchone()
        if existing:
            return dict_from_row(existing), False
        stored = settings.pdf_dir / f"{digest}.pdf"
        stored.write_bytes(content)
        cursor = conn.execute(
            """
            INSERT INTO documents (paper_id, file_path, file_hash, original_name, num_pages, parse_status)
            VALUES (?, ?, ?, ?, ?, 'uploaded')
            """,
            (paper_id, str(stored), digest, file.filename, count_pdf_pages(content)),
        )
        row = conn.execute("SELECT * FROM documents WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict_from_row(row), True


def read_document_text(file_path: str) -> str:
    data = Path(file_path).read_bytes()
    text = data.decode("utf-8", errors="ignore")
    text = re.sub(r"^%PDF-[^\r\n]*(?:\r?\n)?", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or f"Binary document stored at {file_path}. GROBID text extraction was unavailable."


def sections_from_tei(tei: str) -> list[dict]:
    sections: list[dict] = []
    try:
        root = ET.fromstring(tei)
    except ET.ParseError:
        return sections
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    has_namespace = root.tag.startswith("{")

    def xpath(path: str) -> str:
        return path if has_namespace else path.replace("tei:", "")

    def findall(node: ET.Element, path: str) -> list[ET.Element]:
        return node.findall(xpath(path), ns if has_namespace else {})

    def find(node: ET.Element, path: str) -> Optional[ET.Element]:
        return node.find(xpath(path), ns if has_namespace else {})

    def clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def append_section(title: str, content: str, section_type: str) -> None:
        text = clean_text(content)
        if not text:
            return
        sections.append({"seq": len(sections) + 1, "title": title, "content": text, "section_type": section_type})

    def table_rows(table: ET.Element) -> list[str]:
        rows = []
        for row in findall(table, ".//tei:row"):
            cells = [clean_text(" ".join(cell.itertext())) for cell in findall(row, ".//tei:cell")]
            if any(cells):
                rows.append(" ".join(cell for cell in cells if cell))
        return rows

    for abstract in findall(root, ".//tei:text//tei:front//tei:abstract"):
        append_section("Abstract", " ".join(abstract.itertext()), "abstract")

    for div in findall(root, ".//tei:text//tei:body//tei:div"):
        head = find(div, "tei:head")
        paragraphs = [clean_text(" ".join(p.itertext())) for p in findall(div, ".//tei:p")]
        append_section(
            clean_text(" ".join(head.itertext())) if head is not None else f"Section {len(sections) + 1}",
            "\n\n".join(p for p in paragraphs if p),
            "body",
        )

    handled_tables = set()
    for figure in findall(root, ".//tei:text//tei:body//tei:figure"):
        head = find(figure, "tei:head")
        caption = find(figure, "tei:figDesc")
        if figure.get("type") == "table":
            nested_table = find(figure, ".//tei:table")
            if nested_table is not None:
                handled_tables.add(id(nested_table))
            content_parts = []
            if caption is not None:
                content_parts.append(" ".join(caption.itertext()))
            if nested_table is not None:
                content_parts.extend(table_rows(nested_table))
            else:
                content_parts.append(" ".join(figure.itertext()))
            append_section(
                clean_text(" ".join(head.itertext())) if head is not None else f"Table {len(sections) + 1}",
                "\n".join(content_parts),
                "table",
            )
            continue
        append_section(
            clean_text(" ".join(head.itertext())) if head is not None else f"Figure {len(sections) + 1}",
            " ".join(caption.itertext()) if caption is not None else " ".join(figure.itertext()),
            "figure_caption",
        )

    for table in findall(root, ".//tei:text//tei:body//tei:table"):
        if id(table) in handled_tables:
            continue
        head = find(table, "tei:head")
        rows = table_rows(table)
        append_section(
            clean_text(" ".join(head.itertext())) if head is not None else f"Table {len(sections) + 1}",
            "\n".join(rows) or " ".join(table.itertext()),
            "table",
        )

    for idx, bibl in enumerate(findall(root, ".//tei:text//tei:back//tei:listBibl//tei:biblStruct"), start=1):
        append_section(f"Reference {idx}", " ".join(bibl.itertext()), "reference")
    return sections


async def parse_document(document_id: int) -> dict:
    settings = get_settings()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if not row:
            raise ValueError("document not found")
        doc = dict_from_row(row)
        conn.execute("UPDATE documents SET parse_status='parsing', parse_error=NULL WHERE id=?", (document_id,))

    tei_text = None
    sections: list[dict] = []
    grobid = GrobidClient(settings.grobid_url)
    parse_error = None
    try:
        if await grobid.health():
            tei_text = await grobid.process_fulltext(doc["file_path"])
            sections = sections_from_tei(tei_text or "")
            if not sections:
                parse_error = "GROBID returned no body sections; used local text fallback"
        else:
            parse_error = "GROBID is unavailable; used local text fallback"
    except Exception as exc:
        parse_error = f"GROBID parse failed: {exc}; used local text fallback"
        tei_text = None

    if not sections:
        try:
            text = read_document_text(doc["file_path"])
            sections = [{"seq": 1, "title": "Local extracted text", "content": text, "section_type": "body"}]
            tei_text = (
                "<TEI><text><body><div><head>Local extracted text</head>"
                f"<p>{escape(text)}</p></div></body></text></TEI>"
            )
        except Exception as exc:
            with get_conn() as conn:
                conn.execute(
                    "UPDATE documents SET parse_status='failed', parse_error=? WHERE id=?",
                    (f"Local text fallback failed: {exc}", document_id),
                )
                row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
                return dict_from_row(row)

    tei_path = settings.tei_dir / f"document-{document_id}.tei.xml"
    tei_path.write_text(tei_text or "", encoding="utf-8")
    JsonVectorStore(settings.vector_db_path).delete_document(document_id)
    with get_conn() as conn:
        conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM translations WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM reaction_sets WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM sections WHERE document_id=?", (document_id,))
        for item in sections:
            conn.execute(
                """
                INSERT INTO sections (document_id, parent_id, seq, title, content, section_type)
                VALUES (?, NULL, ?, ?, ?, ?)
                """,
                (document_id, item["seq"], item["title"], item["content"], item["section_type"]),
            )
        conn.execute(
            """
            UPDATE documents
            SET parse_status='parsed',
                tei_path=?,
                parse_error=?,
                index_status='not_indexed',
                index_error=NULL,
                chemistry_status='not_extracted',
                chemistry_error=NULL
            WHERE id=?
            """,
            (str(tei_path), parse_error, document_id),
        )
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        return dict_from_row(row)
