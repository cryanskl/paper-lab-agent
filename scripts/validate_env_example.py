#!/usr/bin/env python3
"""Validate that .env.example documents required runtime configuration keys."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REQUIRED_ENV_KEYS = [
    "OPENALEX_MAILTO",
    "UNPAYWALL_EMAIL",
    "GROBID_URL",
    "LLM_API_KEY",
    "EMBEDDING_MODEL",
    "VECTOR_DB_PATH",
    "DATABASE_PATH",
]


def parse_env_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        key, separator, _value = line.partition("=")
        if separator:
            keys.add(key.strip())
    return keys


def missing_required_keys(path: Path) -> list[str]:
    keys = parse_env_keys(path)
    return [key for key in REQUIRED_ENV_KEYS if key not in keys]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate required keys in .env.example")
    parser.add_argument("path", nargs="?", default=".env.example", help="Path to env example file")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"env example not found: {path}", file=sys.stderr)
        return 1

    missing = missing_required_keys(path)
    if missing:
        print(f"env example missing keys: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
