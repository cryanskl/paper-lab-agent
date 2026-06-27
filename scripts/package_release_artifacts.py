#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_release_artifacts import (
    EXPECTED_ARTIFACTS,
    first_symlink_parent,
    format_report,
    validate_release_artifacts,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_filenames() -> list[str]:
    return sorted(EXPECTED_ARTIFACTS.values())


def remove_stale_package_output(output_path: Path) -> str | None:
    try:
        output_path.unlink(missing_ok=True)
    except OSError as exc:
        return f"release package cleanup failed: {exc}"
    return None


def package_release_artifacts(
    artifact_dir: Path,
    output_path: Path,
    *,
    require_clean_source: bool = False,
) -> dict[str, Any]:
    requested_artifact_dir = artifact_dir
    requested_output_path = output_path
    if requested_artifact_dir.is_symlink():
        artifact_dir_path = requested_artifact_dir.absolute()
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir_path),
            "package_path": str(output_path.absolute()),
            "artifact_count": 0,
            "artifact_names": [],
            "package_sha256": None,
            "source": {},
            "service": None,
            "version": None,
            "openapi_path_count": 0,
            "demo_ready": None,
            "demo_counts": {},
            "demo_workflow_statuses": {},
            "demo_export_formats": [],
            "demo_export_audit_entry_counts": {},
            "demo_export_audit_summary_formats": [],
            "demo_reaction_set_verified_by": None,
            "demo_reaction_set_verified_at": None,
            "issues": [f"release artifact directory is not a regular directory: {artifact_dir_path}"],
        }
    symlink_artifact_parent = first_symlink_parent(requested_artifact_dir)
    if symlink_artifact_parent is not None:
        artifact_dir_path = requested_artifact_dir.absolute()
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir_path),
            "package_path": str(output_path.absolute()),
            "artifact_count": 0,
            "artifact_names": [],
            "package_sha256": None,
            "source": {},
            "service": None,
            "version": None,
            "openapi_path_count": 0,
            "demo_ready": None,
            "demo_counts": {},
            "demo_workflow_statuses": {},
            "demo_export_formats": [],
            "demo_export_audit_entry_counts": {},
            "demo_export_audit_summary_formats": [],
            "demo_reaction_set_verified_by": None,
            "demo_reaction_set_verified_at": None,
            "issues": [
                "release artifact directory parent is not a regular directory: "
                f"{symlink_artifact_parent}"
            ],
        }
    artifact_dir = artifact_dir.resolve()
    if requested_output_path.is_symlink():
        package_path = requested_output_path.absolute()
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir),
            "package_path": str(package_path),
            "artifact_count": 0,
            "artifact_names": [],
            "package_sha256": None,
            "source": {},
            "service": None,
            "version": None,
            "openapi_path_count": 0,
            "demo_ready": None,
            "demo_counts": {},
            "demo_workflow_statuses": {},
            "demo_export_formats": [],
            "demo_export_audit_entry_counts": {},
            "demo_export_audit_summary_formats": [],
            "demo_reaction_set_verified_by": None,
            "demo_reaction_set_verified_at": None,
            "issues": [f"release package output is not a regular file: {package_path}"],
        }
    symlink_output_parent = first_symlink_parent(requested_output_path)
    if symlink_output_parent is not None:
        package_path = requested_output_path.absolute()
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir),
            "package_path": str(package_path),
            "artifact_count": 0,
            "artifact_names": [],
            "package_sha256": None,
            "source": {},
            "service": None,
            "version": None,
            "openapi_path_count": 0,
            "demo_ready": None,
            "demo_counts": {},
            "demo_workflow_statuses": {},
            "demo_export_formats": [],
            "demo_export_audit_entry_counts": {},
            "demo_export_audit_summary_formats": [],
            "demo_reaction_set_verified_by": None,
            "demo_reaction_set_verified_at": None,
            "issues": [
                "release package output parent is not a regular directory: "
                f"{symlink_output_parent}"
            ],
        }
    output_path = output_path.resolve()
    output_inside_artifact_dir = output_path == artifact_dir or artifact_dir in output_path.parents
    if output_inside_artifact_dir:
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir),
            "package_path": str(output_path),
            "artifact_count": 0,
            "artifact_names": [],
            "package_sha256": None,
            "source": {},
            "service": None,
            "version": None,
            "openapi_path_count": 0,
            "demo_ready": None,
            "demo_counts": {},
            "demo_workflow_statuses": {},
            "demo_export_formats": [],
            "demo_export_audit_entry_counts": {},
            "demo_export_audit_summary_formats": [],
            "demo_reaction_set_verified_by": None,
            "demo_reaction_set_verified_at": None,
            "issues": ["release package output must not be inside the artifact directory"],
        }
    if output_path.exists() and not output_path.is_file():
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir),
            "package_path": str(output_path),
            "artifact_count": 0,
            "artifact_names": [],
            "package_sha256": None,
            "source": {},
            "service": None,
            "version": None,
            "openapi_path_count": 0,
            "demo_ready": None,
            "demo_counts": {},
            "demo_workflow_statuses": {},
            "demo_export_formats": [],
            "demo_export_audit_entry_counts": {},
            "demo_export_audit_summary_formats": [],
            "demo_reaction_set_verified_by": None,
            "demo_reaction_set_verified_at": None,
            "issues": [f"release package output is not a file: {output_path}"],
        }
    if output_path.parent.exists() and not output_path.parent.is_dir():
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir),
            "package_path": str(output_path),
            "artifact_count": 0,
            "artifact_names": [],
            "package_sha256": None,
            "source": {},
            "service": None,
            "version": None,
            "openapi_path_count": 0,
            "demo_ready": None,
            "demo_counts": {},
            "demo_workflow_statuses": {},
            "demo_export_formats": [],
            "demo_export_audit_entry_counts": {},
            "demo_export_audit_summary_formats": [],
            "demo_reaction_set_verified_by": None,
            "demo_reaction_set_verified_at": None,
            "issues": [f"release package output parent is not a directory: {output_path.parent}"],
        }
    try:
        validation = validate_release_artifacts(artifact_dir, require_clean_source=require_clean_source)
    except Exception as exc:
        cleanup_error = remove_stale_package_output(output_path)
        if cleanup_error:
            return {
                "ok": False,
                "artifact_dir": str(artifact_dir),
                "package_path": str(output_path),
                "artifact_count": 0,
                "artifact_names": [],
                "package_sha256": None,
                "source": {},
                "service": None,
                "version": None,
                "openapi_path_count": 0,
                "demo_ready": None,
                "demo_counts": {},
                "demo_workflow_statuses": {},
                "demo_export_formats": [],
                "demo_export_audit_entry_counts": {},
                "demo_export_audit_summary_formats": [],
                "demo_reaction_set_verified_by": None,
                "demo_reaction_set_verified_at": None,
                "issues": [cleanup_error],
            }
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir),
            "package_path": str(output_path),
            "artifact_count": 0,
            "artifact_names": [],
            "package_sha256": None,
            "source": {},
            "service": None,
            "version": None,
            "openapi_path_count": 0,
            "demo_ready": None,
            "demo_counts": {},
            "demo_workflow_statuses": {},
            "demo_export_formats": [],
            "demo_export_audit_entry_counts": {},
            "demo_export_audit_summary_formats": [],
            "demo_reaction_set_verified_by": None,
            "demo_reaction_set_verified_at": None,
            "issues": [f"release artifact validation failed: {exc}"],
        }
    if validation.get("ok") is not True:
        cleanup_error = remove_stale_package_output(output_path)
        if cleanup_error:
            return {
                "ok": False,
                "artifact_dir": str(artifact_dir),
                "package_path": str(output_path),
                "artifact_count": 0,
                "artifact_names": [],
                "package_sha256": None,
                "source": validation.get("source") or {},
                "service": validation.get("service"),
                "version": validation.get("version"),
                "openapi_path_count": validation.get("openapi_path_count") or 0,
                "demo_ready": validation.get("demo_ready"),
                "demo_counts": validation.get("demo_counts") or {},
                "demo_workflow_statuses": validation.get("demo_workflow_statuses") or {},
                "demo_export_formats": validation.get("demo_export_formats") or [],
                "demo_export_audit_entry_counts": validation.get("demo_export_audit_entry_counts") or {},
                "demo_export_audit_summary_formats": validation.get("demo_export_audit_summary_formats") or [],
                "demo_reaction_set_verified_by": validation.get("demo_reaction_set_verified_by"),
                "demo_reaction_set_verified_at": validation.get("demo_reaction_set_verified_at"),
                "issues": [cleanup_error],
            }
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir),
            "package_path": str(output_path),
            "artifact_count": 0,
            "artifact_names": [],
            "package_sha256": None,
            "source": validation.get("source") or {},
            "service": validation.get("service"),
            "version": validation.get("version"),
            "openapi_path_count": validation.get("openapi_path_count") or 0,
            "demo_ready": validation.get("demo_ready"),
            "demo_counts": validation.get("demo_counts") or {},
            "demo_workflow_statuses": validation.get("demo_workflow_statuses") or {},
            "demo_export_formats": validation.get("demo_export_formats") or [],
            "demo_export_audit_entry_counts": validation.get("demo_export_audit_entry_counts") or {},
            "demo_export_audit_summary_formats": validation.get("demo_export_audit_summary_formats") or [],
            "demo_reaction_set_verified_by": validation.get("demo_reaction_set_verified_by"),
            "demo_reaction_set_verified_at": validation.get("demo_reaction_set_verified_at"),
            "issues": validation.get("issues") or ["release artifact validation failed"],
        }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for filename in artifact_filenames():
                archive.write(artifact_dir / filename, arcname=filename)
    except OSError as exc:
        cleanup_error = remove_stale_package_output(output_path)
        issues = [cleanup_error] if cleanup_error else [f"release package write failed: {exc}"]
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir),
            "package_path": str(output_path),
            "artifact_count": 0,
            "artifact_names": [],
            "package_sha256": None,
            "source": validation.get("source") or {},
            "service": validation.get("service"),
            "version": validation.get("version"),
            "openapi_path_count": validation.get("openapi_path_count") or 0,
            "demo_ready": validation.get("demo_ready"),
            "demo_counts": validation.get("demo_counts") or {},
            "demo_workflow_statuses": validation.get("demo_workflow_statuses") or {},
            "demo_export_formats": validation.get("demo_export_formats") or [],
            "demo_export_audit_entry_counts": validation.get("demo_export_audit_entry_counts") or {},
            "demo_export_audit_summary_formats": validation.get("demo_export_audit_summary_formats") or [],
            "demo_reaction_set_verified_by": validation.get("demo_reaction_set_verified_by"),
            "demo_reaction_set_verified_at": validation.get("demo_reaction_set_verified_at"),
            "issues": issues,
        }

    return {
        "ok": True,
        "artifact_dir": str(artifact_dir),
        "package_path": str(output_path),
        "artifact_count": len(artifact_filenames()),
        "artifact_names": artifact_filenames(),
        "package_sha256": sha256_file(output_path),
        "source": validation.get("source") or {},
        "service": validation.get("service"),
        "version": validation.get("version"),
        "openapi_path_count": validation.get("openapi_path_count") or 0,
        "demo_ready": validation.get("demo_ready"),
        "demo_counts": validation.get("demo_counts") or {},
        "demo_workflow_statuses": validation.get("demo_workflow_statuses") or {},
        "demo_export_formats": validation.get("demo_export_formats") or [],
        "demo_export_audit_entry_counts": validation.get("demo_export_audit_entry_counts") or {},
        "demo_export_audit_summary_formats": validation.get("demo_export_audit_summary_formats") or [],
        "demo_reaction_set_verified_by": validation.get("demo_reaction_set_verified_by"),
        "demo_reaction_set_verified_at": validation.get("demo_reaction_set_verified_at"),
        "issues": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Package validated release handoff artifacts into a zip file.")
    parser.add_argument("--artifact-dir", default="out/release", type=Path, help="Directory with release artifacts.")
    parser.add_argument(
        "--output",
        default="out/paper-lab-agent-release.zip",
        type=Path,
        help="Output zip package path.",
    )
    parser.add_argument(
        "--require-clean-source",
        action="store_true",
        help="Fail when the manifest records a dirty source worktree.",
    )
    parser.add_argument("--compact", action="store_true", help="Emit compact single-line JSON.")
    args = parser.parse_args()

    report = package_release_artifacts(
        args.artifact_dir,
        args.output,
        require_clean_source=args.require_clean_source,
    )
    print(format_report(report, compact=args.compact))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
