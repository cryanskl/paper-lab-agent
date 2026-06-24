import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def configure_storage_defaults() -> None:
    data_dir = os.environ.get("PAPER_LAB_DATA_DIR")
    if not data_dir:
        return
    base = Path(data_dir)
    os.environ.setdefault("DATABASE_PATH", str(base / "plasma.db"))
    os.environ.setdefault("PAPER_LAB_PDF_DIR", str(base / "pdfs"))
    os.environ.setdefault("PAPER_LAB_TEI_DIR", str(base / "tei"))
    os.environ.setdefault("PAPER_LAB_TRANSLATION_DIR", str(base / "translations"))
    os.environ.setdefault("PAPER_LAB_EXPORT_DIR", str(base / "exports"))
    os.environ.setdefault("VECTOR_DB_PATH", str(base / "vector-index.json"))


configure_storage_defaults()

from app.db import init_db
from app.fixture_loader import load_fixture_documents, load_fixture_papers


def main() -> None:
    init_db()
    result = {
        "papers": load_fixture_papers(),
        "documents": load_fixture_documents(),
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
