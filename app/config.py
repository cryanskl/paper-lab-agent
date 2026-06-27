from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def first_symlink_parent(path: Path) -> Optional[Path]:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        return parent
    return None


def is_safe_storage_directory(path: Path) -> bool:
    symlink_parent = first_symlink_parent(path)
    return symlink_parent is None and not path.is_symlink()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = Field(default=Path("data"), alias="PAPER_LAB_DATA_DIR")
    database_path: Path = Field(default=Path("data/plasma.db"), alias="DATABASE_PATH")
    pdf_dir: Path = Field(default=Path("data/pdfs"), alias="PAPER_LAB_PDF_DIR")
    tei_dir: Path = Field(default=Path("data/tei"), alias="PAPER_LAB_TEI_DIR")
    translation_dir: Path = Field(default=Path("data/translations"), alias="PAPER_LAB_TRANSLATION_DIR")
    export_dir: Path = Field(default=Path("data/exports"), alias="PAPER_LAB_EXPORT_DIR")
    vector_db_path: Path = Field(default=Path("data/vector-index.json"), alias="VECTOR_DB_PATH")
    vector_db_backend: str = Field(default="local-json", alias="VECTOR_DB_BACKEND")

    openalex_mailto: Optional[str] = Field(default=None, alias="OPENALEX_MAILTO")
    unpaywall_email: Optional[str] = Field(default=None, alias="UNPAYWALL_EMAIL")
    grobid_url: str = Field(default="http://127.0.0.1:8070", alias="GROBID_URL")
    llm_api_key: Optional[str] = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_BASE_URL")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    embedding_model: str = Field(default="local-hash", alias="EMBEDDING_MODEL")
    scheduler_enabled: bool = Field(default=False, alias="PAPER_LAB_SCHEDULER_ENABLED")
    academic_api_max_pages: int = Field(default=3, alias="ACADEMIC_API_MAX_PAGES")
    academic_api_max_retries: int = Field(default=3, alias="ACADEMIC_API_MAX_RETRIES")
    academic_api_retry_backoff_seconds: float = Field(default=0.25, alias="ACADEMIC_API_RETRY_BACKOFF_SECONDS")
    academic_api_request_interval_seconds: float = Field(default=0.0, alias="ACADEMIC_API_REQUEST_INTERVAL_SECONDS")
    academic_api_timeout_seconds: float = Field(default=20.0, alias="ACADEMIC_API_TIMEOUT_SECONDS")
    unpaywall_api_max_retries: int = Field(default=3, alias="UNPAYWALL_API_MAX_RETRIES")
    unpaywall_api_retry_backoff_seconds: float = Field(default=0.25, alias="UNPAYWALL_API_RETRY_BACKOFF_SECONDS")
    unpaywall_api_request_interval_seconds: float = Field(default=0.0, alias="UNPAYWALL_API_REQUEST_INTERVAL_SECONDS")
    unpaywall_api_timeout_seconds: float = Field(default=20.0, alias="UNPAYWALL_API_TIMEOUT_SECONDS")

    api_prefix: str = "/api/v1"

    @model_validator(mode="after")
    def derive_storage_paths_from_data_dir(self) -> "Settings":
        default_paths = {
            "database_path": Path("data/plasma.db"),
            "pdf_dir": Path("data/pdfs"),
            "tei_dir": Path("data/tei"),
            "translation_dir": Path("data/translations"),
            "export_dir": Path("data/exports"),
            "vector_db_path": Path("data/vector-index.json"),
        }
        derived_defaults = {
            "database_path": self.data_dir / "plasma.db",
            "pdf_dir": self.data_dir / "pdfs",
            "tei_dir": self.data_dir / "tei",
            "translation_dir": self.data_dir / "translations",
            "export_dir": self.data_dir / "exports",
            "vector_db_path": self.data_dir / "vector-index.json",
        }
        for field_name, derived_path in derived_defaults.items():
            current_path = getattr(self, field_name)
            if field_name not in self.model_fields_set or current_path == default_paths[field_name]:
                setattr(self, field_name, derived_path)
        return self

    def ensure_dirs(self) -> None:
        for path in [
            self.data_dir,
            self.database_path.parent,
            self.pdf_dir,
            self.tei_dir,
            self.translation_dir,
            self.export_dir,
            self.vector_db_path.parent,
        ]:
            if not is_safe_storage_directory(path):
                continue
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
