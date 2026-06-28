#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_release_artifacts import export_release_artifacts
from scripts.package_release_artifacts import package_release_artifacts, remove_stale_package_output
from scripts.validate_release_artifacts import validate_release_artifacts
from scripts.validate_release_package import validate_release_package


STAGE_ORDER = ("export", "validate_artifacts", "package", "validate_package")


def stage_state(completed: tuple[str, ...]) -> dict[str, bool]:
    completed_set = set(completed)
    return {stage: stage in completed_set for stage in STAGE_ORDER}


def failed_report(
    stage: str,
    report: dict[str, Any],
    *,
    artifact_dir: Path,
    package_path: Path,
    completed: tuple[str, ...],
) -> dict[str, Any]:
    issues = report.get("issues") if isinstance(report.get("issues"), list) else None
    return {
        "ok": False,
        "stage": stage,
        "artifact_dir": str(artifact_dir.resolve()),
        "package_path": str(package_path.resolve()),
        "package_sha256": report.get("package_sha256"),
        "artifact_names": report.get("artifact_names") or [],
        "source": report.get("source") or {},
        "service": report.get("service"),
        "version": report.get("version"),
        "openapi_path_count": report.get("openapi_path_count") or 0,
        "checksums": report.get("checksums") or {},
        "demo_ready": report.get("demo_ready"),
        "demo_counts": report.get("demo_counts") or {},
        "demo_workflow_statuses": report.get("demo_workflow_statuses") or {},
        "demo_export_formats": report.get("demo_export_formats") or [],
        "demo_export_audit_entry_counts": report.get("demo_export_audit_entry_counts") or {},
        "demo_export_audit_summary_formats": report.get("demo_export_audit_summary_formats") or [],
        "demo_reaction_set_verified_by": report.get("demo_reaction_set_verified_by"),
        "demo_reaction_set_verified_at": report.get("demo_reaction_set_verified_at"),
        "stages": stage_state(completed),
        "issues": issues or [f"release handoff {stage} failed"],
    }


def failed_report_after_stale_package_cleanup(
    stage: str,
    report: dict[str, Any],
    *,
    artifact_dir: Path,
    package_path: Path,
    completed: tuple[str, ...],
) -> dict[str, Any]:
    cleanup_error = remove_stale_package_output(package_path)
    failure = failed_report(
        stage,
        report,
        artifact_dir=artifact_dir,
        package_path=package_path,
        completed=completed,
    )
    if cleanup_error:
        failure["issues"] = [cleanup_error]
    return failure


def build_release_handoff(
    artifact_dir: Path,
    package_path: Path,
    *,
    require_clean_source: bool = False,
    compact_artifacts: bool = False,
) -> dict[str, Any]:
    artifact_dir = artifact_dir.resolve()
    package_path = package_path.resolve()

    export_report = export_release_artifacts(artifact_dir, compact=compact_artifacts)
    if export_report.get("ok") is False:
        return failed_report_after_stale_package_cleanup(
            "export",
            export_report,
            artifact_dir=artifact_dir,
            package_path=package_path,
            completed=(),
        )

    artifact_validation = validate_release_artifacts(
        artifact_dir,
        require_clean_source=require_clean_source,
    )
    if artifact_validation.get("ok") is not True:
        return failed_report_after_stale_package_cleanup(
            "validate_artifacts",
            artifact_validation,
            artifact_dir=artifact_dir,
            package_path=package_path,
            completed=("export",),
        )

    package_report = package_release_artifacts(
        artifact_dir,
        package_path,
        require_clean_source=require_clean_source,
    )
    if package_report.get("ok") is not True:
        return failed_report(
            "package",
            package_report,
            artifact_dir=artifact_dir,
            package_path=package_path,
            completed=("export", "validate_artifacts"),
        )

    package_validation = validate_release_package(
        package_path,
        require_clean_source=require_clean_source,
    )
    if package_validation.get("ok") is not True:
        return failed_report(
            "validate_package",
            package_validation,
            artifact_dir=artifact_dir,
            package_path=package_path,
            completed=("export", "validate_artifacts", "package"),
        )

    return {
        "ok": True,
        "stage": "complete",
        "artifact_dir": package_report.get("artifact_dir") or str(artifact_dir),
        "package_path": package_validation.get("package_path") or str(package_path),
        "package_sha256": package_validation.get("package_sha256"),
        "artifact_names": package_validation.get("artifact_names") or [],
        "source": package_validation.get("source") or {},
        "service": package_validation.get("service"),
        "version": package_validation.get("version"),
        "openapi_path_count": package_validation.get("openapi_path_count") or 0,
        "checksums": package_validation.get("checksums") or {},
        "demo_ready": package_validation.get("demo_ready"),
        "demo_counts": package_validation.get("demo_counts") or {},
        "demo_workflow_statuses": package_validation.get("demo_workflow_statuses") or {},
        "demo_export_formats": package_validation.get("demo_export_formats") or [],
        "demo_export_audit_entry_counts": package_validation.get("demo_export_audit_entry_counts") or {},
        "demo_export_audit_summary_formats": package_validation.get("demo_export_audit_summary_formats") or [],
        "demo_reaction_set_verified_by": package_validation.get("demo_reaction_set_verified_by"),
        "demo_reaction_set_verified_at": package_validation.get("demo_reaction_set_verified_at"),
        "stages": stage_state(STAGE_ORDER),
        "issues": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build, package, and validate release handoff artifacts in one command."
    )
    parser.add_argument(
        "--artifact-dir",
        default="out/release",
        type=Path,
        help="Directory for release artifact files.",
    )
    parser.add_argument(
        "--package",
        dest="package_path",
        default="out/paper-lab-agent-release.zip",
        type=Path,
        help="Output release zip package path.",
    )
    parser.add_argument(
        "--require-clean-source",
        action="store_true",
        help="Fail when the generated manifest records a dirty source worktree.",
    )
    parser.add_argument("--compact", action="store_true", help="Emit compact single-line JSON.")
    args = parser.parse_args()

    report = build_release_handoff(
        args.artifact_dir,
        args.package_path,
        require_clean_source=args.require_clean_source,
        compact_artifacts=args.compact,
    )
    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            separators=(",", ":") if args.compact else None,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
