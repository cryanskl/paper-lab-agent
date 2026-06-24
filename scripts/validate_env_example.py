#!/usr/bin/env python3
"""Validate that .env.example documents required runtime configuration keys."""

from __future__ import annotations

import ast
import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_CONFIG_PATH = REPO_ROOT / "app" / "config.py"

REQUIRED_ENV_KEYS = [
    "OPENALEX_MAILTO",
    "UNPAYWALL_EMAIL",
    "GROBID_URL",
    "LLM_API_KEY",
    "EMBEDDING_MODEL",
    "VECTOR_DB_PATH",
    "DATABASE_PATH",
]
SECRET_LIKE_ENV_KEYS = [
    "OPENALEX_MAILTO",
    "UNPAYWALL_EMAIL",
    "LLM_API_KEY",
]


def settings_env_aliases(path: Path = SETTINGS_CONFIG_PATH) -> list[str]:
    if not path.exists():
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    aliases: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Settings":
            continue
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.value, ast.Call):
                continue
            if getattr(statement.value.func, "id", "") != "Field":
                continue
            for keyword in statement.value.keywords:
                if keyword.arg == "alias" and isinstance(keyword.value, ast.Constant):
                    aliases.append(str(keyword.value.value))
    return aliases


def required_env_keys(config_path: Path = SETTINGS_CONFIG_PATH) -> list[str]:
    keys: list[str] = []
    for key in [*REQUIRED_ENV_KEYS, *settings_env_aliases(config_path)]:
        if key not in keys:
            keys.append(key)
    return keys


def parse_env_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for key, _value in parse_env_values(path).items():
        keys.add(key)
    return keys


def parse_env_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        key, separator, _value = line.partition("=")
        if separator:
            values[key.strip()] = _value.strip().strip('"').strip("'")
    return values


def missing_required_keys(path: Path) -> list[str]:
    keys = parse_env_keys(path)
    return [key for key in required_env_keys() if key not in keys]


def non_empty_secret_like_keys(path: Path) -> list[str]:
    values = parse_env_values(path)
    return [key for key in SECRET_LIKE_ENV_KEYS if values.get(key)]


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
    filled_secret_like_keys = non_empty_secret_like_keys(path)
    if filled_secret_like_keys:
        print(f"env example secret-like keys must be blank: {', '.join(filled_secret_like_keys)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
