from __future__ import annotations

import argparse
import sys
from pathlib import Path


REQUIRED_GITIGNORE_PATTERNS = [
    ".env",
    ".venv/",
    "data/",
    ".uv-cache/",
    ".pytest_cache/",
    ".next/",
    "__pycache__/",
]


def load_gitignore_patterns(path: Path) -> set[str]:
    patterns: set[str] = set()
    if not path.exists():
        return patterns
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.add(line)
    return patterns


def missing_required_gitignore_patterns(path: Path) -> list[str]:
    patterns = load_gitignore_patterns(path)
    return [pattern for pattern in REQUIRED_GITIGNORE_PATTERNS if pattern not in patterns]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release hygiene ignore rules.")
    parser.add_argument("gitignore", nargs="?", default=".gitignore", type=Path)
    args = parser.parse_args()

    missing = missing_required_gitignore_patterns(args.gitignore)
    if missing:
        print(f"gitignore missing patterns: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
