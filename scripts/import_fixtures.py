import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import init_db
from app.fixture_loader import load_fixture_documents, load_fixture_papers


def main() -> None:
    init_db()
    result = {
        "papers": load_fixture_papers(),
        "documents": load_fixture_documents(),
    }
    print(result)


if __name__ == "__main__":
    main()
