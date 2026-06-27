import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional, Protocol

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


class EmbeddingAdapter(Protocol):
    model_name: str

    def embed(self, text: str) -> list[float]:
        ...


class LocalHashEmbeddingAdapter:
    model_name = "local-hash"

    def embed(self, text: str) -> list[float]:
        return local_hash_embedding(text)


SUPPORTED_EMBEDDING_MODELS = {"local-hash"}
SUPPORTED_VECTOR_DB_BACKENDS = {"local-json"}
SOURCE_EXCERPT_MAX_CHARS = 360


def normalize_vector_db_backend(backend: Optional[str]) -> str:
    return (backend or "local-json").strip().lower()


def get_embedding_adapter(model_name: str) -> EmbeddingAdapter:
    normalized = (model_name or "local-hash").strip().lower()
    if normalized == "local-hash":
        return LocalHashEmbeddingAdapter()
    raise ValueError(f"unsupported embedding model: {model_name}")


def source_excerpt(text: str, max_chars: int = SOURCE_EXCERPT_MAX_CHARS) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars].rstrip()}..."


def source_citation(item: dict) -> str:
    paper_id = item.get("_paper_id") if "_paper_id" in item else item.get("paper_id")
    paper_title = item.get("_paper_title") or item.get("paper_title")
    section_id = item.get("_section_id") if "_section_id" in item else item.get("section_id")
    section_seq = item.get("_section_seq") if "_section_seq" in item else item.get("section_seq")
    section_title = item.get("_section_title") or item.get("section_title")
    section_type = item.get("_section_type") or item.get("section_type")
    chunk_id = item.get("_chunk_id") or item.get("id") or item.get("chunk_id")
    parts = []
    if paper_id is not None:
        parts.append(f"paper_id={paper_id}")
    else:
        parts.append(f"document_id={item.get('document_id')}")
    if paper_title:
        parts.append(f"title={paper_title}")
    if section_title:
        parts.append(f"section={section_title}")
    if section_id is not None:
        parts.append(f"section_id={section_id}")
    if section_seq is not None:
        parts.append(f"section_seq={section_seq}")
    if section_type:
        parts.append(f"section_type={section_type}")
    if chunk_id is not None:
        parts.append(f"chunk_id={chunk_id}")
    return "Source: " + "; ".join(parts)


def answer_with_citation(text: str, source: dict) -> str:
    return f"{source_excerpt(text, 600)}\n\n{source_citation(source)}"


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def assert_safe_vector_store_path(path: Path) -> None:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        raise ValueError(f"vector store path parent is not a regular directory: {parent}")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"vector store path is not a regular file: {path}")


def is_vector_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse_vector_store_json(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"vector store JSON is invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("vector store JSON must be an object")
    for vector_id, record in data.items():
        if not isinstance(record, dict):
            raise ValueError(f"vector store record must be an object: {vector_id}")
        embedding = record.get("embedding")
        if not isinstance(embedding, list):
            raise ValueError(f"vector store record embedding must be a numeric array: {vector_id}")
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in embedding):
            raise ValueError(f"vector store record embedding must be a numeric array: {vector_id}")
        if any(not is_vector_number(value) for value in embedding):
            raise ValueError(f"vector store record embedding must be a finite numeric array: {vector_id}")
    return data


class JsonVectorStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        assert_safe_vector_store_path(self.path)
        return parse_vector_store_json(self.path.read_text(encoding="utf-8"))

    def upsert_many(self, records: dict[str, dict]) -> None:
        existing = self.load()
        existing.update(records)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        assert_safe_vector_store_path(self.path)
        self.path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    def delete_document(self, document_id: int) -> None:
        existing = self.load()
        filtered = {
            vector_id: record
            for vector_id, record in existing.items()
            if record.get("document_id") != document_id
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        assert_safe_vector_store_path(self.path)
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


def get_vector_store(settings) -> JsonVectorStore:
    normalized = normalize_vector_db_backend(settings.vector_db_backend)
    if normalized == "local-json":
        return JsonVectorStore(settings.vector_db_path)
    raise ValueError(f"unsupported vector db backend: {settings.vector_db_backend}")


def chunk_text(text: str, max_words: int = 220) -> Iterable[str]:
    words = text.split()
    if not words:
        return []
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]


def mark_index_queued(document_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        conn.execute(
            "UPDATE documents SET index_status='indexing', index_error=NULL WHERE id=?",
            (document_id,),
        )


def index_document(document_id: int) -> dict:
    settings = get_settings()
    vector_store = None
    vector_index = {}
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET index_status='indexing', index_error=NULL WHERE id=?",
            (document_id,),
        )
        sections = conn.execute("SELECT * FROM sections WHERE document_id=? ORDER BY seq", (document_id,)).fetchall()
        if not sections:
            error = "document has no parsed sections"
            conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            try:
                vector_store = get_vector_store(settings)
                vector_store.delete_document(document_id)
            except Exception as exc:
                error = f"{error}; vector cleanup failed: {exc}"
            conn.execute(
                "UPDATE documents SET index_status='failed', index_error=? WHERE id=?",
                (error, document_id),
            )
            return {"document_id": document_id, "chunks": 0, "embedded": 0, "status": "failed", "error": error}
        count = 0
        try:
            vector_store = get_vector_store(settings)
            conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            vector_store.delete_document(document_id)
            embedding_adapter = get_embedding_adapter(settings.embedding_model)
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
                    embedding = embedding_adapter.embed(chunk)
                    vector_index[vector_id] = {
                        "chunk_id": cursor.lastrowid,
                        "document_id": document_id,
                        "section_id": section["id"],
                        "text": chunk,
                        "embedding": embedding,
                        "embedding_model": embedding_adapter.model_name,
                        "vector_db_backend": settings.vector_db_backend,
                        "dimensions": len(embedding),
                    }
                    count += 1
            if count == 0:
                raise ValueError("document has no indexable section text")
            vector_store.delete_document(document_id)
            vector_store.upsert_many(vector_index)
            conn.execute(
                "UPDATE documents SET index_status='indexed', index_error=NULL WHERE id=?",
                (document_id,),
            )
            return {"document_id": document_id, "chunks": count, "embedded": 1, "status": "indexed"}
        except Exception as exc:
            conn.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
            if vector_store is not None:
                try:
                    vector_store.delete_document(document_id)
                except Exception:
                    pass
            conn.execute(
                "UPDATE documents SET index_status='failed', index_error=? WHERE id=?",
                (str(exc), document_id),
            )
            return {"document_id": document_id, "chunks": 0, "embedded": 0, "status": "failed", "error": str(exc)}


def query(question: str, document_ids: list[int], top_k: int) -> dict:
    settings = get_settings()
    vector_store = get_vector_store(settings)
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
                    SELECT
                        ch.id, ch.document_id, ch.section_id, ch.vector_id, ch.text,
                        s.seq AS section_seq,
                        s.title AS section_title,
                        s.section_type AS section_type,
                        d.paper_id AS paper_id,
                        p.title AS paper_title
                    FROM chunks ch
                    LEFT JOIN sections s ON s.id = ch.section_id
                    LEFT JOIN documents d ON d.id = ch.document_id
                    LEFT JOIN papers p ON p.id = d.paper_id
                    WHERE ch.embedded=1 AND ch.id IN ({placeholders})
                    """,
                    chunk_ids,
                ).fetchall()
                chunks_by_id = {row["id"]: dict_from_row(row) for row in rows}
            if vector_ids:
                placeholders = ",".join("?" for _ in vector_ids)
                rows = conn.execute(
                    f"""
                    SELECT
                        ch.id, ch.document_id, ch.section_id, ch.vector_id, ch.text,
                        s.seq AS section_seq,
                        s.title AS section_title,
                        s.section_type AS section_type,
                        d.paper_id AS paper_id,
                        p.title AS paper_title
                    FROM chunks ch
                    LEFT JOIN sections s ON s.id = ch.section_id
                    LEFT JOIN documents d ON d.id = ch.document_id
                    LEFT JOIN papers p ON p.id = d.paper_id
                    WHERE ch.embedded=1 AND ch.vector_id IN ({placeholders})
                    """,
                    vector_ids,
                ).fetchall()
                chunks_by_vector = {row["vector_id"]: dict_from_row(row) for row in rows}
        validated_hits = []
        for hit in vector_hits:
            chunk = chunks_by_id.get(hit.get("chunk_id")) or chunks_by_vector.get(hit.get("vector_id"))
            if not chunk or chunk["document_id"] != hit["document_id"]:
                continue
            chunk_text_value = chunk.get("text") or ""
            if hit.get("embedding_model") == "local-hash" and score(question_terms, chunk_text_value) <= 0:
                continue
            item = dict(hit)
            item["_chunk_id"] = chunk["id"]
            item["_section_id"] = chunk["section_id"]
            item["_section_seq"] = chunk["section_seq"]
            item["_section_title"] = chunk["section_title"]
            item["_section_type"] = chunk["section_type"]
            item["_paper_id"] = chunk["paper_id"]
            item["_paper_title"] = chunk["paper_title"]
            item["_text"] = chunk_text_value
            validated_hits.append(item)
        vector_hits = validated_hits
    if vector_hits:
        return {
            "answer": answer_with_citation(vector_hits[0].get("_text") or vector_hits[0]["text"], vector_hits[0]),
            "sources": [
                {
                    "document_id": item["document_id"],
                    "paper_id": item.get("_paper_id"),
                    "paper_title": item.get("_paper_title"),
                    "section_id": item.get("_section_id"),
                    "section_seq": item.get("_section_seq"),
                    "section_title": item.get("_section_title"),
                    "section_type": item.get("_section_type"),
                    "chunk_id": item.get("_chunk_id"),
                    "vector_id": item["vector_id"],
                    "score": round(item["_score"], 3),
                    "source_excerpt": source_excerpt(item.get("_text") or item.get("text") or ""),
                }
                for item in vector_hits
            ],
        }

    params = []
    conditions = ["ch.embedded=1"]
    if document_ids:
        placeholders = ",".join("?" for _ in document_ids)
        conditions.append(f"ch.document_id IN ({placeholders})")
        params.extend(document_ids)
    where = f"WHERE {' AND '.join(conditions)}"
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT
                ch.*,
                s.seq AS section_seq,
                s.title AS section_title,
                s.section_type AS section_type,
                d.paper_id AS paper_id,
                p.title AS paper_title
            FROM chunks ch
            LEFT JOIN sections s ON s.id = ch.section_id
            LEFT JOIN documents d ON d.id = ch.document_id
            LEFT JOIN papers p ON p.id = d.paper_id
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
    answer = answer_with_citation(selected[0]["text"], selected[0])
    return {
        "answer": answer,
        "sources": [
            {
                "document_id": item["document_id"],
                "paper_id": item.get("paper_id"),
                "paper_title": item.get("paper_title"),
                "section_id": item.get("section_id"),
                "section_seq": item.get("section_seq"),
                "section_title": item["section_title"],
                "section_type": item.get("section_type"),
                "chunk_id": item["id"],
                "vector_id": item.get("vector_id"),
                "score": round(item["_score"], 3),
                "source_excerpt": source_excerpt(item.get("text") or ""),
            }
            for item in selected
        ],
    }
