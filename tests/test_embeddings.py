import pytest

from app.config import Settings
from app.routers.system import config_warnings
from app.services.rag import get_embedding_adapter


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


def test_config_warnings_report_unsupported_embedding_model():
    warnings = config_warnings(Settings(EMBEDDING_MODEL="text-embedding-3-small"))

    assert {
        "code": "unsupported_embedding_model",
        "capability": "rag_indexing",
        "message": "EMBEDDING_MODEL=text-embedding-3-small is not supported by the local adapter registry.",
    } in warnings


def test_config_warnings_accept_supported_embedding_model_case_insensitively():
    warnings = config_warnings(Settings(EMBEDDING_MODEL="LOCAL-HASH"))

    assert not any(warning["code"] == "unsupported_embedding_model" for warning in warnings)


def test_config_warnings_report_unsupported_vector_db_backend():
    warnings = config_warnings(Settings(VECTOR_DB_BACKEND="faiss"))

    assert {
        "code": "unsupported_vector_db_backend",
        "capability": "rag_indexing",
        "message": "VECTOR_DB_BACKEND=faiss is not supported by the current vector store registry.",
    } in warnings


def test_config_warnings_accept_supported_vector_db_backend_case_insensitively():
    warnings = config_warnings(Settings(VECTOR_DB_BACKEND="LOCAL-JSON"))

    assert not any(warning["code"] == "unsupported_vector_db_backend" for warning in warnings)
