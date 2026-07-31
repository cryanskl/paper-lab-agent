from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings


STORAGE_ENV_KEYS = (
    "DATABASE_PATH",
    "PAPER_LAB_PDF_DIR",
    "PAPER_LAB_TEI_DIR",
    "PAPER_LAB_TRANSLATION_DIR",
    "PAPER_LAB_EXPORT_DIR",
    "VECTOR_DB_PATH",
)


def clear_storage_env(monkeypatch):
    for key in STORAGE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_data_dir_drives_default_local_storage_paths(tmp_path, monkeypatch):
    clear_storage_env(monkeypatch)
    data_dir = tmp_path / "paper-lab-data"

    settings = Settings(_env_file=None, PAPER_LAB_DATA_DIR=data_dir)

    assert settings.data_dir == data_dir
    assert settings.database_path == data_dir / "plasma.db"
    assert settings.pdf_dir == data_dir / "pdfs"
    assert settings.tei_dir == data_dir / "tei"
    assert settings.translation_dir == data_dir / "translations"
    assert settings.export_dir == data_dir / "exports"
    assert settings.vector_db_path == data_dir / "chroma"


def test_explicit_storage_paths_override_data_dir_defaults(tmp_path, monkeypatch):
    clear_storage_env(monkeypatch)
    data_dir = tmp_path / "paper-lab-data"
    database_path = tmp_path / "custom" / "custom.db"
    pdf_dir = tmp_path / "custom-pdfs"
    vector_db_path = tmp_path / "custom-vector.json"

    settings = Settings(
        _env_file=None,
        PAPER_LAB_DATA_DIR=data_dir,
        DATABASE_PATH=database_path,
        PAPER_LAB_PDF_DIR=pdf_dir,
        VECTOR_DB_PATH=vector_db_path,
    )

    assert settings.database_path == database_path
    assert settings.pdf_dir == pdf_dir
    assert settings.vector_db_path == vector_db_path
    assert settings.tei_dir == data_dir / "tei"
    assert settings.translation_dir == data_dir / "translations"
    assert settings.export_dir == data_dir / "exports"


def test_builtin_default_storage_values_follow_custom_data_dir(tmp_path, monkeypatch):
    clear_storage_env(monkeypatch)
    data_dir = tmp_path / "paper-lab-data"

    settings = Settings(
        _env_file=None,
        PAPER_LAB_DATA_DIR=data_dir,
        DATABASE_PATH=Path("data/plasma.db"),
        PAPER_LAB_PDF_DIR=Path("data/pdfs"),
        PAPER_LAB_TRANSLATION_DIR=Path("data/translations"),
    )

    assert settings.database_path == data_dir / "plasma.db"
    assert settings.pdf_dir == data_dir / "pdfs"
    assert settings.translation_dir == data_dir / "translations"


def test_ensure_dirs_skips_symlinked_data_dir_before_creating_children(tmp_path, monkeypatch):
    clear_storage_env(monkeypatch)
    outside_dir = tmp_path / "outside-data"
    outside_dir.mkdir()
    data_dir = tmp_path / "paper-lab-data"
    data_dir.symlink_to(outside_dir, target_is_directory=True)
    settings = Settings(_env_file=None, PAPER_LAB_DATA_DIR=data_dir)

    settings.ensure_dirs()

    assert not (outside_dir / "pdfs").exists()
    assert not (outside_dir / "tei").exists()
    assert not (outside_dir / "translations").exists()
    assert not (outside_dir / "exports").exists()


def test_rag_chunk_settings_accept_valid_token_budget():
    settings = Settings(
        _env_file=None,
        RAG_CHUNK_TARGET_TOKENS=320,
        RAG_CHUNK_MAX_TOKENS=480,
        RAG_CHUNK_OVERLAP_TOKENS=48,
    )

    assert settings.rag_chunk_target_tokens == 320
    assert settings.rag_chunk_max_tokens == 480
    assert settings.rag_chunk_overlap_tokens == 48


@pytest.mark.parametrize(
    ("target", "maximum", "overlap", "message"),
    [
        (700, 600, 60, "must not exceed"),
        (450, 600, 450, "must be smaller"),
    ],
)
def test_rag_chunk_settings_reject_invalid_token_budget(target, maximum, overlap, message):
    with pytest.raises(ValidationError, match=message):
        Settings(
            _env_file=None,
            RAG_CHUNK_TARGET_TOKENS=target,
            RAG_CHUNK_MAX_TOKENS=maximum,
            RAG_CHUNK_OVERLAP_TOKENS=overlap,
        )
