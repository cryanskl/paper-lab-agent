import json
import math
import re
from collections import Counter
from pathlib import Path
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


def local_hash_embedding(text: str, dimensions: int = 64) -> list[float]:
    vector = [0.0] * dimensions
    for token in tokenize(text):
        index = sum(ord(char) for char in token) % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


class JsonVectorStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def upsert_many(self, records: dict[str, dict]) -> None:
        existing = self.load()
        existing.update(records)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    def delete_document(self, document_id: int) -> None:
        existing = self.load()
        filtered = {
            vector_id: record
            for vector_id, record in existing.items()
            if record.get("document_id") != document_id
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")

    def search(self, query_embedding: list[float], document_ids: list[int], top_k: int) -> list[dict]:
        records = self.load()
        selected = []
        allowed = set(document_ids)
        for vector_id, record in records.items():
            if allowed and record.get("document_id") not in allowed:
                continue
            similarity = cosine_similarity(query_embedding, record.get("embedding") or [])
            if similarity > 0:
                item = dict(record)
                item["vector_id"] = vector_id
                item["_score"] = similarity
                selected.append(item)
        selected.sort(key=lambda item: item["_score"], reverse=True)
        return selected[:top_k]


def chunk_text(text: str, max_words: int = 220) -> Iterable[str]:
    words = text.split()
    if not words:
        return []
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]


def mark_index_queued(document_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET index_status='indexing', index_error=NULL WHERE id=?",
            (document_id,),
        )


def index_document(document_id: int) -> dict:
    settings = get_settings()
    vector_store = JsonVectorStore(settings.vector_db_path)
    vector_index = {}
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET index_status='indexing', index_error=NULL WHERE id=?",
            (document_id,),
        )
        sections = conn.execute("SELECT * FROM sections WHERE document_id=? ORDER BY seq", (document_id,)).fetchall()
        if not sections:
            conn.execute(
                "UPDATE documents SET index_status='failed', index_error=? WHERE id=?",
                ("document has no parsed sections", document_id),
            )
            return {"document_id": document_id, "chunks": 0, "embedded": 0, "status": "failed"}
        conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        count = 0
        try:
            for section in sections:
                for seq, chunk in enumerate(chunk_text(section["content"] or ""), start=1):
                    vector_id = f"doc-{document_id}-section-{section['id']}-chunk-{seq}"
                    cursor = conn.execute(
                        """
                        INSERT INTO chunks (document_id, section_id, seq, text, token_count, vector_id, embedded)
                        VALUES (?, ?, ?, ?, ?, ?, 1)
                        """,
                        (document_id, section["id"], seq, chunk, len(tokenize(chunk)), vector_id),
                    )
                    embedding = local_hash_embedding(chunk)
                    vector_index[vector_id] = {
                        "chunk_id": cursor.lastrowid,
                        "document_id": document_id,
                        "section_id": section["id"],
                        "text": chunk,
                        "embedding": embedding,
                        "embedding_model": "local-hash",
                        "dimensions": len(embedding),
                    }
                    count += 1
            vector_store.delete_document(document_id)
            vector_store.upsert_many(vector_index)
            conn.execute(
                "UPDATE documents SET index_status='indexed', index_error=NULL WHERE id=?",
                (document_id,),
            )
            return {"document_id": document_id, "chunks": count, "embedded": 1, "status": "indexed"}
        except Exception as exc:
            conn.execute(
                "UPDATE documents SET index_status='failed', index_error=? WHERE id=?",
                (str(exc), document_id),
            )
            return {"document_id": document_id, "chunks": count, "embedded": 0, "status": "failed"}


def query(question: str, document_ids: list[int], top_k: int) -> dict:
    settings = get_settings()
    vector_store = JsonVectorStore(settings.vector_db_path)
    question_terms = Counter(tokenize(question))
    vector_hits = vector_store.search(local_hash_embedding(question), document_ids, top_k)
    vector_hits = [
        hit
        for hit in vector_hits
        if hit.get("embedding_model") != "local-hash" or score(question_terms, hit.get("text") or "") > 0
    ]
    if vector_hits:
        chunk_ids = [hit["chunk_id"] for hit in vector_hits if hit.get("chunk_id")]
        vector_ids = [hit["vector_id"] for hit in vector_hits if hit.get("vector_id")]
        chunks_by_id = {}
        chunks_by_vector = {}
        with get_conn() as conn:
            if chunk_ids:
                placeholders = ",".join("?" for _ in chunk_ids)
                rows = conn.execute(
                    f"""
                    SELECT ch.id, ch.document_id, ch.vector_id, s.title AS section_title
                    FROM chunks ch
                    LEFT JOIN sections s ON s.id = ch.section_id
                    WHERE ch.id IN ({placeholders})
                    """,
                    chunk_ids,
                ).fetchall()
                chunks_by_id = {row["id"]: dict_from_row(row) for row in rows}
            if vector_ids:
                placeholders = ",".join("?" for _ in vector_ids)
                rows = conn.execute(
                    f"""
                    SELECT ch.id, ch.document_id, ch.vector_id, s.title AS section_title
                    FROM chunks ch
                    LEFT JOIN sections s ON s.id = ch.section_id
                    WHERE ch.vector_id IN ({placeholders})
                    """,
                    vector_ids,
                ).fetchall()
                chunks_by_vector = {row["vector_id"]: dict_from_row(row) for row in rows}
        validated_hits = []
        for hit in vector_hits:
            chunk = chunks_by_id.get(hit.get("chunk_id")) or chunks_by_vector.get(hit.get("vector_id"))
            if not chunk or chunk["document_id"] != hit["document_id"]:
                continue
            item = dict(hit)
            item["_chunk_id"] = chunk["id"]
            item["_section_title"] = chunk["section_title"]
            validated_hits.append(item)
        vector_hits = validated_hits
    if vector_hits:
        return {
            "answer": vector_hits[0]["text"][:600],
            "sources": [
                {
                    "document_id": item["document_id"],
                    "section_title": item.get("_section_title"),
                    "chunk_id": item.get("_chunk_id"),
                    "vector_id": item["vector_id"],
                    "score": round(item["_score"], 3),
                }
                for item in vector_hits
            ],
        }

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
                "vector_id": item.get("vector_id"),
                "score": round(item["_score"], 3),
            }
            for item in selected
        ],
    }
