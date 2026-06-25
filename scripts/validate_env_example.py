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
SCRIPT_RUNTIME_ENV_KEYS = [
    "API_HOST",
    "API_PORT",
    "API_BASE_URL",
    "STREAMLIT_HOST",
    "STREAMLIT_PORT",
    "FRONTEND_URL",
    "DEV_READY_TIMEOUT",
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


def settings_env_defaults(path: Path = SETTINGS_CONFIG_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    tree = ast.parse(path.read_text(encoding="utf-8"))
    defaults: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Settings":
            continue
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.value, ast.Call):
                continue
            if getattr(statement.value.func, "id", "") != "Field":
                continue
            alias = None
            default = None
            for keyword in statement.value.keywords:
                if keyword.arg == "alias" and isinstance(keyword.value, ast.Constant):
                    alias = str(keyword.value.value)
                elif keyword.arg == "default":
                    default = env_default_value(keyword.value)
            if alias is not None and default is not None:
                defaults[alias] = default
    return defaults


def env_default_value(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant):
        if node.value is None:
            return ""
        if isinstance(node.value, bool):
            return str(node.value).lower()
        return str(node.value)
    if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Path" and node.args:
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Constant):
            return str(first_arg.value)
    return None


def required_env_keys(config_path: Path = SETTINGS_CONFIG_PATH) -> list[str]:
    keys: list[str] = []
    for key in [*REQUIRED_ENV_KEYS, *settings_env_aliases(config_path), *SCRIPT_RUNTIME_ENV_KEYS]:
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


def normalize_env_value(value: str) -> str:
    if value.startswith("./"):
        return value[2:]
    return value


def env_values_match(actual: str, expected: str) -> bool:
    if normalize_env_value(actual) == normalize_env_value(expected):
        return True
    try:
        return float(actual) == float(expected)
    except ValueError:
        return False


def documented_default_mismatches(path: Path, config_path: Path = SETTINGS_CONFIG_PATH) -> list[str]:
    values = parse_env_values(path)
    mismatches: list[str] = []
    for key, expected in settings_env_defaults(config_path).items():
        if key not in values:
            continue
        actual = values[key]
        if not env_values_match(actual, expected):
            mismatches.append(f"{key} expected {expected}, got {actual}")
    return mismatches


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
    mismatches = documented_default_mismatches(path)
    if mismatches:
        print(f"env example defaults drifted: {', '.join(mismatches)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
