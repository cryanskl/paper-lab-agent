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
from scripts.validate_release_artifacts import first_symlink_parent


EXPECTED_ARTIFACT_NAMES = {"openapi.json", "demo-summary.json", "release-manifest.json"}
DEMO_WORKFLOW_STATUS_KEYS = [
    "parse_status",
    "index_status",
    "chemistry_status",
    "translation_status",
    "reaction_set_status",
]


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


def git_dirty() -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return bool(result.stdout.strip())


def source_metadata() -> dict[str, Any]:
    return {
        "git_commit": git_value(["rev-parse", "HEAD"]),
        "git_branch": git_value(["branch", "--show-current"]),
        "git_dirty": git_dirty(),
    }


def demo_workflow_statuses(demo_summary: dict[str, Any]) -> dict[str, Any]:
    return {key: demo_summary.get(key) for key in DEMO_WORKFLOW_STATUS_KEYS}


def write_json(path: Path, payload: dict[str, Any], *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload,
        ensure_ascii=False,
        indent=None if compact else 2,
        separators=(",", ":") if compact else None,
    )
    path.write_text(f"{text}\n", encoding="utf-8")


def remove_artifacts(paths: tuple[Path, ...]) -> str | None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            return f"release artifact cleanup failed: {exc}"
    return None


def export_release_artifacts(output_dir: Path, *, compact: bool = False) -> dict[str, Any]:
    requested_output_dir = output_dir
    if requested_output_dir.is_symlink():
        output_dir = requested_output_dir.absolute()
        return {
            "ok": False,
            "output_dir": str(output_dir),
            "issues": [f"release artifact output directory is not a regular directory: {output_dir}"],
        }
    symlink_parent = first_symlink_parent(requested_output_dir)
    if symlink_parent is not None:
        return {
            "ok": False,
            "output_dir": str(requested_output_dir.absolute()),
            "issues": [
                "release artifact output directory parent is not a regular directory: "
                f"{symlink_parent}"
            ],
        }
    output_dir = output_dir.resolve()
    if output_dir.exists() and not output_dir.is_dir():
        return {
            "ok": False,
            "output_dir": str(output_dir),
            "issues": [f"release artifact output directory is not a directory: {output_dir}"],
        }
    if output_dir.exists():
        unexpected_files = sorted(
            path.name for path in output_dir.iterdir() if path.name not in EXPECTED_ARTIFACT_NAMES
        )
        if unexpected_files:
            return {
                "ok": False,
                "output_dir": str(output_dir),
                "issues": [
                    f"release artifact output directory contains unexpected files: {unexpected_files!r}"
                ],
            }
        unsafe_artifact_path_issues = []
        for path in sorted((output_dir / name for name in EXPECTED_ARTIFACT_NAMES), key=lambda item: item.name):
            if path.exists() and path.is_symlink():
                unsafe_artifact_path_issues.append(
                    f"release artifact output path is not a regular file: {path}"
                )
            elif path.exists() and not path.is_file():
                unsafe_artifact_path_issues.append(f"release artifact output path is not a file: {path}")
        if unsafe_artifact_path_issues:
            return {
                "ok": False,
                "output_dir": str(output_dir),
                "issues": unsafe_artifact_path_issues,
            }
    output_dir.mkdir(parents=True, exist_ok=True)
    openapi_path = output_dir / "openapi.json"
    demo_summary_path = output_dir / "demo-summary.json"
    manifest_path = output_dir / "release-manifest.json"
    for artifact_path in (openapi_path, demo_summary_path, manifest_path):
        try:
            artifact_path.unlink(missing_ok=True)
        except OSError as exc:
            return {
                "ok": False,
                "output_dir": str(output_dir),
                "issues": [f"release artifact cleanup failed: {exc}"],
            }

    openapi_error = write_openapi(openapi_path, compact=compact)
    if openapi_error:
        return {
            "ok": False,
            "output_dir": str(output_dir),
            "issues": [f"OpenAPI artifact write failed: {openapi_error}"],
        }
    try:
        demo_payload = prepare_demo_data()
    except Exception as exc:
        return {
            "ok": False,
            "output_dir": str(output_dir),
            "issues": [f"Demo data preparation failed: {exc}"],
        }
    demo_summary = demo_payload["summary"]
    try:
        write_json(demo_summary_path, demo_summary, compact=compact)
    except OSError as exc:
        cleanup_error = remove_artifacts((openapi_path, demo_summary_path, manifest_path))
        return {
            "ok": False,
            "output_dir": str(output_dir),
            "issues": [cleanup_error or f"Demo summary artifact write failed: {exc}"],
        }

    manifest = {
        "service": "paper-lab-agent",
        "version": __version__,
        "artifacts": {
            "openapi": openapi_path.name,
            "demo_summary": demo_summary_path.name,
            "manifest": manifest_path.name,
        },
        "artifact_count": len(EXPECTED_ARTIFACT_NAMES),
        "demo_ready": demo_summary.get("ready") is True,
        "demo_counts": demo_summary.get("counts") or {},
        "demo_workflow_statuses": demo_workflow_statuses(demo_summary),
        "demo_export_formats": demo_summary.get("export_formats") or [],
        "demo_export_audit_entry_counts": demo_summary.get("export_audit_entry_counts") or {},
        "demo_export_audit_summary_formats": demo_summary.get("export_audit_summary_formats") or [],
        "demo_reaction_set_verified_by": demo_summary.get("reaction_set_verified_by"),
        "demo_reaction_set_verified_at": demo_summary.get("reaction_set_verified_at"),
        "openapi_path_count": len(json.loads(openapi_path.read_text(encoding="utf-8")).get("paths", {})),
        "source": source_metadata(),
        "checksums": {
            openapi_path.name: sha256_file(openapi_path),
            demo_summary_path.name: sha256_file(demo_summary_path),
            manifest_path.name: "",
        },
    }
    manifest["checksums"][manifest_path.name] = manifest_checksum(manifest)
    try:
        write_json(manifest_path, manifest, compact=compact)
    except OSError as exc:
        cleanup_error = remove_artifacts((openapi_path, demo_summary_path, manifest_path))
        return {
            "ok": False,
            "output_dir": str(output_dir),
            "issues": [cleanup_error or f"Release manifest artifact write failed: {exc}"],
        }
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
    return 1 if manifest.get("ok") is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
