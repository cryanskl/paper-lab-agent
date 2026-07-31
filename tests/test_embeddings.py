import pytest

from app.config import Settings
from app.routers.system import config_warnings
from app.services import rag as rag_service
from app.services.rag import ChromaVectorStore, get_embedding_adapter


def test_local_hash_embedding_adapter_is_deterministic_and_named():
    adapter = get_embedding_adapter("local-hash")

    first = adapter.embed("argon plasma chemistry")
    second = adapter.embed("argon plasma chemistry")

    assert adapter.model_name == "local-hash"
    assert first == second
    assert len(first) == 64


def test_embedding_adapter_rejects_unsupported_model():
    with pytest.raises(ValueError, match="unsupported embedding model: text-embedding-3-small"):
        get_embedding_adapter("text-embedding-3-small")


def test_bge_m3_embedding_adapter_normalizes_and_validates_output(monkeypatch):
    calls = []

    class FakeVector:
        def tolist(self):
            return [0.25, -0.5, 0.75]

    class FakeModel:
        def encode(self, text, **kwargs):
            calls.append((text, kwargs))
            return FakeVector()

    monkeypatch.setattr(rag_service, "load_bge_m3_model", lambda: FakeModel())

    adapter = get_embedding_adapter(" BGE-M3 ")
    vector = adapter.embed("  中文问题\n  English evidence  ")

    assert adapter.model_name == "bge-m3"
    assert vector == [0.25, -0.5, 0.75]
    assert calls == [
        (
            "中文问题 English evidence",
            {
                "normalize_embeddings": True,
                "convert_to_numpy": True,
                "show_progress_bar": False,
            },
        )
    ]


def test_chroma_vector_store_persists_queries_and_deletes(tmp_path):
    store = ChromaVectorStore(tmp_path / "chroma")
    store.upsert_many(
        {
            "vector-1": {
                "chunk_id": 11,
                "document_id": 7,
                "section_id": 3,
                "text": "argon plasma evidence",
                "embedding": [1.0, 0.0, 0.0],
                "embedding_model": "bge-m3",
                "vector_db_backend": "chroma",
                "dimensions": 3,
            }
        }
    )

    reloaded = ChromaVectorStore(tmp_path / "chroma")
    hits = reloaded.search([1.0, 0.0, 0.0], [7], 3)

    assert list(reloaded.load()) == ["vector-1"]
    assert hits[0]["vector_id"] == "vector-1"
    assert hits[0]["embedding_model"] == "bge-m3"
    assert hits[0]["_score"] == pytest.approx(1.0)

    reloaded.delete_document(7)
    assert reloaded.load() == {}


def test_config_warnings_report_unsupported_embedding_model():
    warnings = config_warnings(Settings(EMBEDDING_MODEL="text-embedding-3-small"))

    warning = next(warning for warning in warnings if warning["code"] == "unsupported_embedding_model")
    assert warning["capability"] == "rag_indexing"
    assert warning["actual"] == "text-embedding-3-small"
    assert warning["supported"] == ["bge-m3", "local-hash"]
    assert warning["message"] == "EMBEDDING_MODEL=text-embedding-3-small is not supported by the local adapter registry."


def test_config_warnings_accept_supported_embedding_model_case_insensitively():
    warnings = config_warnings(Settings(EMBEDDING_MODEL="LOCAL-HASH"))

    assert not any(warning["code"] == "unsupported_embedding_model" for warning in warnings)


def test_config_warnings_report_unsupported_vector_db_backend():
    warnings = config_warnings(Settings(VECTOR_DB_BACKEND="faiss"))

    warning = next(warning for warning in warnings if warning["code"] == "unsupported_vector_db_backend")
    assert warning["capability"] == "rag_indexing"
    assert warning["actual"] == "faiss"
    assert warning["supported"] == ["chroma", "local-json"]
    assert warning["message"] == "VECTOR_DB_BACKEND=faiss is not supported by the current vector store registry."


def test_config_warnings_accept_supported_vector_db_backend_case_insensitively():
    warnings = config_warnings(Settings(VECTOR_DB_BACKEND="LOCAL-JSON"))

    assert not any(warning["code"] == "unsupported_vector_db_backend" for warning in warnings)
