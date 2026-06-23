import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.clients.grobid import GrobidClient
from app.config import get_settings
from app.db import dict_from_row, get_conn
from app.utils import now_iso


async def save_upload(file: UploadFile, paper_id: Optional[int]) -> tuple[dict, bool]:
    settings = get_settings()
    content = await file.read()
    digest = hashlib.sha256(content).hexdigest()
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM documents WHERE file_hash=?", (digest,)).fetchone()
        if existing:
            return dict_from_row(existing), False
        suffix = Path(file.filename or "paper.pdf").suffix or ".pdf"
        stored = settings.pdf_dir / f"{digest}{suffix}"
        stored.write_bytes(content)
        cursor = conn.execute(
            """
            INSERT INTO documents (paper_id, file_path, file_hash, original_name, num_pages, parse_status)
            VALUES (?, ?, ?, ?, ?, 'uploaded')
            """,
            (paper_id, str(stored), digest, file.filename, None),
        )
        row = conn.execute("SELECT * FROM documents WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict_from_row(row), True


def read_document_text(file_path: str) -> str:
    data = Path(file_path).read_bytes()
    text = data.decode("utf-8", errors="ignore")
    text = re.sub(r"\s+", " ", text).strip()
    return text or f"Binary document stored at {file_path}. GROBID text extraction was unavailable."


def sections_from_tei(tei: str) -> list[dict]:
    sections: list[dict] = []
    try:
        root = ET.fromstring(tei)
    except ET.ParseError:
        return sections
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    divs = root.findall(".//tei:text//tei:body//tei:div", ns)
    for idx, div in enumerate(divs, start=1):
        head = div.find("tei:head", ns)
        paragraphs = [" ".join(p.itertext()).strip() for p in div.findall(".//tei:p", ns)]
        content = "\n\n".join(p for p in paragraphs if p)
        if content:
            sections.append(
                {
                    "seq": idx,
                    "title": " ".join(head.itertext()).strip() if head is not None else f"Section {idx}",
                    "content": content,
                    "section_type": "body",
                }
            )
    return sections


async def parse_document(document_id: int) -> dict:
    settings = get_settings()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if not row:
            raise ValueError("document not found")
        doc = dict_from_row(row)
        conn.execute("UPDATE documents SET parse_status='parsing' WHERE id=?", (document_id,))

    tei_text = None
    sections: list[dict] = []
    grobid = GrobidClient(settings.grobid_url)
    try:
        if await grobid.health():
            tei_text = await grobid.process_fulltext(doc["file_path"])
            sections = sections_from_tei(tei_text or "")
    except Exception:
        tei_text = None

    if not sections:
        text = read_document_text(doc["file_path"])
        sections = [{"seq": 1, "title": "Local extracted text", "content": text, "section_type": "body"}]
        tei_text = f"<TEI><text><body><div><head>Local extracted text</head><p>{text}</p></div></body></text></TEI>"

    tei_path = settings.tei_dir / f"document-{document_id}.tei.xml"
    tei_path.write_text(tei_text or "", encoding="utf-8")
    with get_conn() as conn:
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
            "UPDATE documents SET parse_status='parsed', tei_path=? WHERE id=?",
            (str(tei_path), document_id),
        )
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        return dict_from_row(row)

