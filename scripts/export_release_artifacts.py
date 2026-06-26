#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import __version__
from scripts.export_openapi import write_openapi
from scripts.prepare_demo_data import prepare_demo_data


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_checksum(payload: dict[str, Any]) -> str:
    canonical = json.loads(json.dumps(payload))
    checksums = canonical.get("checksums")
    if isinstance(checksums, dict):
        checksums["release-manifest.json"] = ""
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def git_value(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def source_metadata() -> dict[str, str]:
    return {
        "git_commit": git_value(["rev-parse", "HEAD"]),
        "git_branch": git_value(["branch", "--show-current"]),
    }


def write_json(path: Path, payload: dict[str, Any], *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload,
        ensure_ascii=False,
        indent=None if compact else 2,
        separators=(",", ":") if compact else None,
    )
    path.write_text(f"{text}\n", encoding="utf-8")


def export_release_artifacts(output_dir: Path, *, compact: bool = False) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    openapi_path = output_dir / "openapi.json"
    demo_summary_path = output_dir / "demo-summary.json"
    manifest_path = output_dir / "release-manifest.json"

    write_openapi(openapi_path, compact=compact)
    demo_payload = prepare_demo_data()
    demo_summary = demo_payload["summary"]
    write_json(demo_summary_path, demo_summary, compact=compact)

    manifest = {
        "service": "paper-lab-agent",
        "version": __version__,
        "artifacts": {
            "openapi": openapi_path.name,
            "demo_summary": demo_summary_path.name,
            "manifest": manifest_path.name,
        },
        "demo_ready": demo_summary.get("ready") is True,
        "demo_export_formats": demo_summary.get("export_formats") or [],
        "openapi_path_count": len(json.loads(openapi_path.read_text(encoding="utf-8")).get("paths", {})),
        "source": source_metadata(),
        "checksums": {
            openapi_path.name: sha256_file(openapi_path),
            demo_summary_path.name: sha256_file(demo_summary_path),
            manifest_path.name: "",
        },
    }
    manifest["checksums"][manifest_path.name] = manifest_checksum(manifest)
    write_json(manifest_path, manifest, compact=compact)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Export release handoff artifacts.")
    parser.add_argument("--output-dir", default="out", type=Path, help="Directory for release artifact files.")
    parser.add_argument("--compact", action="store_true", help="Write compact single-line JSON files.")
    args = parser.parse_args()

    manifest = export_release_artifacts(args.output_dir, compact=args.compact)
    print(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            separators=(",", ":") if args.compact else None,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
