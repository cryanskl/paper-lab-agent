import json
import re
from collections import Counter
from typing import Iterable

from app.config import get_settings
from app.db import dict_from_row, get_conn


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_+\-/]+", text.lower())


def score(question_terms: Counter, text: str) -> float:
    terms = Counter(tokenize(text))
    if not question_terms or not terms:
        return 0.0
    overlap = sum(min(question_terms[t], terms[t]) for t in question_terms)
    return overlap / max(1, sum(question_terms.values()))


def chunk_text(text: str, max_words: int = 220) -> Iterable[str]:
    words = text.split()
    if not words:
        return []
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]


def index_document(document_id: int) -> dict:
    settings = get_settings()
    with get_conn() as conn:
        sections = conn.execute("SELECT * FROM sections WHERE document_id=? ORDER BY seq", (document_id,)).fetchall()
        if not sections:
            raise ValueError("document has no parsed sections")
        conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        count = 0
        vector_index = {}
        for section in sections:
            for seq, chunk in enumerate(chunk_text(section["content"] or ""), start=1):
                vector_id = f"doc-{document_id}-section-{section['id']}-chunk-{seq}"
                conn.execute(
                    """
                    INSERT INTO chunks (document_id, section_id, seq, text, token_count, vector_id, embedded)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    """,
                    (document_id, section["id"], seq, chunk, len(tokenize(chunk)), vector_id),
                )
                vector_index[vector_id] = {"document_id": document_id, "section_id": section["id"], "text": chunk}
                count += 1
        existing = {}
        if settings.vector_db_path.exists():
            try:
                existing = json.loads(settings.vector_db_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {}
        existing.update(vector_index)
        settings.vector_db_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"document_id": document_id, "chunks": count, "embedded": 1}


def query(question: str, document_ids: list[int], top_k: int) -> dict:
    question_terms = Counter(tokenize(question))
    params = []
    where = ""
    if document_ids:
        placeholders = ",".join("?" for _ in document_ids)
        where = f"WHERE ch.document_id IN ({placeholders})"
        params.extend(document_ids)
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT ch.*, s.title AS section_title
            FROM chunks ch
            LEFT JOIN sections s ON s.id = ch.section_id
            {where}
            """,
            params,
        ).fetchall()
    scored = []
    for row in rows:
        item = dict_from_row(row)
        item["_score"] = score(question_terms, item["text"] or "")
        if item["_score"] > 0:
            scored.append(item)
    scored.sort(key=lambda item: item["_score"], reverse=True)
    selected = scored[:top_k]
    if not selected:
        return {"answer": "证据不足：当前索引中没有检索到足够相关的段落。", "sources": []}
    answer = selected[0]["text"][:600]
    return {
        "answer": answer,
        "sources": [
            {
                "document_id": item["document_id"],
                "section_title": item["section_title"],
                "chunk_id": item["id"],
                "score": round(item["_score"], 3),
            }
            for item in selected
        ],
    }

