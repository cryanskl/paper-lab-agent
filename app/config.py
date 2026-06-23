from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = Field(default=Path("data"), alias="PAPER_LAB_DATA_DIR")
    database_path: Path = Field(default=Path("data/plasma.db"), alias="DATABASE_PATH")
    pdf_dir: Path = Field(default=Path("data/pdfs"), alias="PAPER_LAB_PDF_DIR")
    tei_dir: Path = Field(default=Path("data/tei"), alias="PAPER_LAB_TEI_DIR")
    translation_dir: Path = Field(default=Path("data/translations"), alias="PAPER_LAB_TRANSLATION_DIR")
    export_dir: Path = Field(default=Path("data/exports"), alias="PAPER_LAB_EXPORT_DIR")
    vector_db_path: Path = Field(default=Path("data/vector-index.json"), alias="VECTOR_DB_PATH")

    openalex_mailto: Optional[str] = Field(default=None, alias="OPENALEX_MAILTO")
    unpaywall_email: Optional[str] = Field(default=None, alias="UNPAYWALL_EMAIL")
    grobid_url: str = Field(default="http://127.0.0.1:8070", alias="GROBID_URL")
    llm_api_key: Optional[str] = Field(default=None, alias="LLM_API_KEY")
    embedding_model: str = Field(default="local-fixture", alias="EMBEDDING_MODEL")

    api_prefix: str = "/api/v1"

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
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
