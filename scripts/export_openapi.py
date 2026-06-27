#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.main import app


def openapi_payload() -> dict[str, Any]:
    return app.openapi()


def write_openapi(output_path: Path, *, compact: bool = False) -> str | None:
    if output_path.is_symlink():
        return f"output path is not a regular file: {output_path}"
    symlink_parent = first_symlink_parent(output_path)
    if symlink_parent is not None:
        return f"output path parent is not a regular directory: {symlink_parent}"
    if output_path.exists() and not output_path.is_file():
        return f"output path is not a regular file: {output_path}"
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(format_openapi(compact=compact), encoding="utf-8")
    except OSError as exc:
        return f"failed to write output file {output_path}: {exc}"
    return None


def first_symlink_parent(path: Path) -> Path | None:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        return parent
    return None


def print_openapi(stream: TextIO = sys.stdout, *, compact: bool = False) -> None:
    stream.write(format_openapi(compact=compact))
    stream.write("\n")


def format_openapi(*, compact: bool = False) -> str:
    if compact:
        return json.dumps(openapi_payload(), ensure_ascii=False, separators=(",", ":"))
    return json.dumps(openapi_payload(), ensure_ascii=False, indent=2, sort_keys=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the FastAPI OpenAPI schema without starting the server.")
    parser.add_argument("--output", type=Path, help="Write the OpenAPI JSON schema to this path instead of stdout.")
    parser.add_argument("--compact", action="store_true", help="Emit compact single-line JSON.")
    args = parser.parse_args()

    if args.output is None:
        print_openapi(compact=args.compact)
    else:
        output_error = write_openapi(args.output, compact=args.compact)
        if output_error:
            print(f"export_openapi failed: {output_error}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
