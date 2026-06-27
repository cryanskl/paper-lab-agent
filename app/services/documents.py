import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
from urllib.parse import unquote
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


def safe_original_filename(filename: Optional[str]) -> str:
    decoded = unquote(filename or "")
    basename = decoded.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = "".join(char for char in basename if ord(char) >= 32).strip()
    return cleaned or "document.pdf"


def mark_parse_queued(document_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM translations WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM reaction_sets WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM sections WHERE document_id=?", (document_id,))
        conn.execute(
            """
            UPDATE documents
            SET parse_status='parsing',
                parse_error=NULL,
                index_status='not_indexed',
                index_error=NULL,
                chemistry_status='not_extracted',
                chemistry_error=NULL
            WHERE id=?
            """,
            (document_id,),
        )


def assert_safe_document_storage_path(path: Path) -> None:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        raise OSError(f"document storage path parent is not a regular directory: {parent}")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise OSError(f"document storage path is not a regular file: {path}")


async def save_upload(file: UploadFile, paper_id: Optional[int]) -> tuple[dict, bool]:
    settings = get_settings()
    content = await file.read()
    digest = hashlib.sha256(content).hexdigest()
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM documents WHERE file_hash=?", (digest,)).fetchone()
        if existing:
            return dict_from_row(existing), False
        stored = settings.pdf_dir / f"{digest}.pdf"
        assert_safe_document_storage_path(stored)
        stored.write_bytes(content)
        cursor = conn.execute(
            """
            INSERT INTO documents (paper_id, file_path, file_hash, original_name, num_pages, parse_status)
            VALUES (?, ?, ?, ?, ?, 'uploaded')
            """,
            (paper_id, str(stored), digest, safe_original_filename(file.filename), count_pdf_pages(content)),
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

    def clean_mixed_text(parts: list[str]) -> str:
        text = clean_text(" ".join(part for part in parts if part))
        return re.sub(r"\s+([,.;:!?])", r"\1", text)

    def local_name(node: ET.Element) -> str:
        return node.tag.rsplit("}", 1)[-1]

    def text_content(node: ET.Element, include_targets: bool = True) -> str:
        parts = [node.text or ""]
        for child in list(node):
            child_text = text_content(child, include_targets)
            if include_targets and local_name(child) in {"ptr", "ref"}:
                target = clean_text(child.get("target") or "")
                if target:
                    child_text = f"{child_text} ({target})" if child_text else target
            parts.append(child_text)
            parts.append(child.tail or "")
        return clean_mixed_text(parts)

    def append_section(title: str, content: str, section_type: str) -> None:
        text = clean_text(content)
        if not text:
            return
        sections.append({"seq": len(sections) + 1, "title": title, "content": text, "section_type": section_type})

    def table_rows(table: ET.Element) -> list[str]:
        rows = []
        for row in findall(table, ".//tei:row"):
            cells = [text_content(cell) for cell in findall(row, ".//tei:cell")]
            if any(cells):
                rows.append(" ".join(cell for cell in cells if cell))
        return rows

    def child_notes(node: ET.Element) -> list[str]:
        notes = []
        for child in list(node):
            if local_name(child) == "note":
                note = text_content(child)
                if note:
                    notes.append(note)
        return notes

    def title_from_head_or_label(node: ET.Element, fallback: str) -> str:
        head = find(node, "tei:head")
        if head is not None:
            title = text_content(head, include_targets=False)
            if title:
                return title
        label = find(node, "tei:label")
        if label is not None:
            title = text_content(label, include_targets=False)
            if title:
                return title
        return fallback

    def content_without_children(
        node: ET.Element, excluded: list[Optional[ET.Element]], include_targets: bool = True
    ) -> str:
        excluded_children = [excluded_child for excluded_child in excluded if excluded_child is not None]
        parts = [node.text or ""]
        for child in list(node):
            if all(child is not excluded_child for excluded_child in excluded_children):
                parts.append(text_content(child, include_targets=include_targets))
            parts.append(child.tail or "")
        return clean_mixed_text(parts)

    def content_without_descendants(
        node: ET.Element, excluded: list[Optional[ET.Element]], include_targets: bool = True
    ) -> str:
        excluded_ids = {id(excluded_node) for excluded_node in excluded if excluded_node is not None}

        def collect(current: ET.Element) -> str:
            parts = [current.text or ""]
            for child in list(current):
                if id(child) in excluded_ids:
                    parts.append(child.tail or "")
                    continue
                child_text = collect(child)
                if include_targets and local_name(child) in {"ptr", "ref"}:
                    target = clean_text(child.get("target") or "")
                    if target:
                        child_text = f"{child_text} ({target})" if child_text else target
                parts.append(child_text)
                parts.append(child.tail or "")
            return clean_mixed_text(parts)

        return collect(node)

    def date_value(date: ET.Element) -> str:
        text = text_content(date, include_targets=False)
        if text:
            return text
        for attr in ["when", "from", "to", "notBefore", "notAfter"]:
            value = clean_text(date.get(attr) or "")
            if value:
                return value
        return ""

    def bibliographic_scope_value(scope: ET.Element) -> str:
        text = text_content(scope, include_targets=False)
        if text:
            return text
        start = clean_text(scope.get("from") or "")
        end = clean_text(scope.get("to") or "")
        if start and end:
            return f"{start}-{end}"
        return start or end

    def reference_text(bibl: ET.Element) -> str:
        id_nodes = findall(bibl, ".//tei:idno")
        attribute_nodes = [
            node
            for node in bibl.iter()
            if (
                local_name(node) == "date"
                and date_value(node)
                and not text_content(node, include_targets=False)
            )
            or (
                local_name(node) == "biblScope"
                and bibliographic_scope_value(node)
                and not text_content(node, include_targets=False)
            )
        ]
        text = content_without_descendants(bibl, [*id_nodes, *attribute_nodes], include_targets=False)
        parts = [text] if text else []
        seen_values = {text} if text else set()
        for attr_node in attribute_nodes:
            value = date_value(attr_node) if local_name(attr_node) == "date" else bibliographic_scope_value(attr_node)
            if value and value not in seen_values:
                parts.append(value)
                seen_values.add(value)
        for id_node in id_nodes:
            value = text_content(id_node, include_targets=False)
            if not value or value in seen_values:
                continue
            id_type = clean_text(id_node.get("type") or "").upper()
            label = id_type or "ID"
            parts.append(f"{label}: {value}")
            seen_values.add(value)
        for node in bibl.iter():
            if local_name(node) not in {"ptr", "ref"}:
                continue
            target = clean_text(node.get("target") or "")
            if not target or target in seen_values:
                continue
            parts.append(f"URL: {target}")
            seen_values.add(target)
        return clean_text(" ".join(parts))

    abstract_nodes = [
        *findall(root, ".//tei:teiHeader//tei:profileDesc//tei:abstract"),
        *findall(root, ".//tei:text//tei:front//tei:abstract"),
    ]
    seen_abstracts = set()
    for abstract in abstract_nodes:
        head = find(abstract, "tei:head")
        abstract_content = clean_text(
            content_without_children(abstract, [head]) if head is not None else text_content(abstract)
        )
        if not abstract_content or abstract_content in seen_abstracts:
            continue
        seen_abstracts.add(abstract_content)
        append_section("Abstract", abstract_content, "abstract")

    def append_body_div(div: ET.Element) -> None:
        head = find(div, "tei:head")
        explicit_title = text_content(head, include_targets=False) if head is not None else None
        content_parts = []

        def flush_body_content() -> None:
            nonlocal content_parts
            title = explicit_title or f"Section {len(sections) + 1}"
            append_section(title, "\n\n".join(item for item in content_parts if item), "body")
            content_parts = []

        for child in list(div):
            child_name = local_name(child)
            if child_name == "head":
                continue
            if child_name == "p":
                content_parts.append(text_content(child))
            elif child_name == "list":
                content_parts.extend(text_content(item) for item in findall(child, "tei:item"))
            elif child_name == "div":
                flush_body_content()
                append_body_div(child)
            elif child_name == "figure":
                flush_body_content()
                append_figure(child)
            elif child_name == "table":
                flush_body_content()
                append_table(child)
        flush_body_content()

    def append_figure(figure: ET.Element) -> None:
        head = find(figure, "tei:head")
        label = find(figure, "tei:label")
        caption = find(figure, "tei:figDesc")
        if figure.get("type") == "table":
            nested_table = find(figure, ".//tei:table")
            content_parts = []
            if caption is not None:
                content_parts.append(text_content(caption))
            if nested_table is not None:
                content_parts.extend(table_rows(nested_table))
                content_parts.extend(child_notes(figure))
            else:
                fallback_content = content_without_children(figure, [head, label, caption])
                if fallback_content:
                    content_parts.append(fallback_content)
            append_section(
                title_from_head_or_label(figure, f"Table {len(sections) + 1}"),
                "\n".join(content_parts),
                "table",
            )
            return
        append_section(
            title_from_head_or_label(figure, f"Figure {len(sections) + 1}"),
            text_content(caption) if caption is not None else content_without_children(figure, [head, label]),
            "figure_caption",
        )

    def append_table(table: ET.Element) -> None:
        head = find(table, "tei:head")
        label = find(table, "tei:label")
        content_parts = table_rows(table)
        content_parts.extend(child_notes(table))
        append_section(
            title_from_head_or_label(table, f"Table {len(sections) + 1}"),
            "\n".join(content_parts) or content_without_children(table, [head, label]),
            "table",
        )

    for body in findall(root, ".//tei:text//tei:body"):
        pending_body_head = None
        content_parts = []

        def flush_body_content() -> None:
            nonlocal content_parts, pending_body_head
            title = pending_body_head or f"Section {len(sections) + 1}"
            append_section(title, "\n\n".join(item for item in content_parts if item), "body")
            content_parts = []
            pending_body_head = None

        for child in list(body):
            child_name = local_name(child)
            if child_name == "head":
                flush_body_content()
                pending_body_head = text_content(child, include_targets=False)
            elif child_name == "div":
                flush_body_content()
                append_body_div(child)
            elif child_name == "p":
                content_parts.append(text_content(child))
            elif child_name == "list":
                content_parts.extend(text_content(item) for item in findall(child, "tei:item"))
            elif child_name == "figure":
                flush_body_content()
                append_figure(child)
            elif child_name == "table":
                flush_body_content()
                append_table(child)
        flush_body_content()

    reference_index = 1
    for list_bibl in findall(root, ".//tei:text//tei:back//tei:listBibl"):
        for bibl in list(list_bibl):
            if local_name(bibl) not in {"biblStruct", "biblFull", "bibl"}:
                continue
            append_section(f"Reference {reference_index}", reference_text(bibl), "reference")
            reference_index += 1
    return sections


async def parse_document(document_id: int) -> dict:
    settings = get_settings()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        if not row:
            raise ValueError("document not found")
        doc = dict_from_row(row)
        conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM translations WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM reaction_sets WHERE document_id=?", (document_id,))
        conn.execute("DELETE FROM sections WHERE document_id=?", (document_id,))
        conn.execute(
            """
            UPDATE documents
            SET parse_status='parsing',
                parse_error=NULL,
                index_status='not_indexed',
                index_error=NULL,
                chemistry_status='not_extracted',
                chemistry_error=NULL
            WHERE id=?
            """,
            (document_id,),
        )

    tei_text = None
    sections: list[dict] = []
    grobid = GrobidClient(settings.grobid_url)
    parse_error = None
    try:
        assert_safe_document_storage_path(Path(doc["file_path"]))
    except Exception as exc:
        parse_error = f"Document source validation failed: {exc}"
        try:
            JsonVectorStore(settings.vector_db_path).delete_document(document_id)
        except Exception as cleanup_exc:
            parse_error = f"{parse_error}; vector cleanup failed: {cleanup_exc}"
        with get_conn() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM translations WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM reaction_sets WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM sections WHERE document_id=?", (document_id,))
            conn.execute(
                """
                UPDATE documents
                SET parse_status='failed',
                    parse_error=?,
                    index_status='not_indexed',
                    index_error=NULL,
                    chemistry_status='not_extracted',
                    chemistry_error=NULL
                WHERE id=?
                """,
                (parse_error, document_id),
            )
            row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
            return dict_from_row(row)

    try:
        grobid_health = await grobid.health_detail()
        if grobid_health.get("available"):
            tei_text = await grobid.process_fulltext(doc["file_path"])
            sections = sections_from_tei(tei_text or "")
            has_body_content = any(item.get("section_type") != "reference" for item in sections)
            if not has_body_content:
                sections = []
                parse_error = "GROBID returned no body sections; used local text fallback"
        else:
            reason_parts = [
                str(grobid_health.get("error") or "unavailable"),
                f"url={grobid_health.get('url')}",
            ]
            if grobid_health.get("status_code") is not None:
                reason_parts.append(f"status_code={grobid_health.get('status_code')}")
            parse_error = f"GROBID is unavailable ({'; '.join(reason_parts)}); used local text fallback"
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
            parse_error = f"Local text fallback failed: {exc}"
            try:
                JsonVectorStore(settings.vector_db_path).delete_document(document_id)
            except Exception as cleanup_exc:
                parse_error = f"{parse_error}; vector cleanup failed: {cleanup_exc}"
            with get_conn() as conn:
                conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
                conn.execute("DELETE FROM translations WHERE document_id=?", (document_id,))
                conn.execute("DELETE FROM reaction_sets WHERE document_id=?", (document_id,))
                conn.execute("DELETE FROM sections WHERE document_id=?", (document_id,))
                conn.execute(
                    """
                    UPDATE documents
                    SET parse_status='failed',
                        parse_error=?,
                        index_status='not_indexed',
                        index_error=NULL,
                        chemistry_status='not_extracted',
                        chemistry_error=NULL
                    WHERE id=?
                    """,
                    (parse_error, document_id),
                )
                row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
                return dict_from_row(row)

    try:
        tei_path = settings.tei_dir / f"document-{document_id}.tei.xml"
        assert_safe_document_storage_path(tei_path)
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
    except Exception as exc:
        with get_conn() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM translations WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM reaction_sets WHERE document_id=?", (document_id,))
            conn.execute("DELETE FROM sections WHERE document_id=?", (document_id,))
            conn.execute(
                """
                UPDATE documents
                SET parse_status='failed',
                    parse_error=?,
                    index_status='not_indexed',
                    index_error=NULL,
                    chemistry_status='not_extracted',
                    chemistry_error=NULL
                WHERE id=?
                """,
                (f"Parse finalization failed: {exc}", document_id),
            )
            row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
            return dict_from_row(row)
