#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.package_release_artifacts import artifact_filenames, sha256_file
from scripts.validate_release_artifacts import first_symlink_parent, format_report, validate_release_artifacts


def is_unsafe_archive_name(name: str) -> bool:
    posix_path = PurePosixPath(name)
    windows_path = PureWindowsPath(name)
    return (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or bool(windows_path.root)
        or ".." in posix_path.parts
        or ".." in windows_path.parts
    )


def validate_release_package(package_path: Path, *, require_clean_source: bool = False) -> dict[str, Any]:
    requested_package_path = package_path
    if requested_package_path.is_symlink():
        package_path = requested_package_path.absolute()
        return {
            "ok": False,
            "package_path": str(package_path),
            "package_sha256": None,
            "artifact_count": 0,
            "artifact_names": [],
            "source": {},
            "demo_ready": None,
            "demo_export_formats": [],
            "demo_export_audit_entry_counts": {},
            "demo_reaction_set_verified_by": None,
            "demo_reaction_set_verified_at": None,
            "issues": [f"release package is not a regular file: {package_path}"],
        }
    symlink_parent = first_symlink_parent(requested_package_path)
    if symlink_parent is not None:
        package_path = requested_package_path.absolute()
        return {
            "ok": False,
            "package_path": str(package_path),
            "package_sha256": None,
            "artifact_count": 0,
            "artifact_names": [],
            "source": {},
            "demo_ready": None,
            "demo_export_formats": [],
            "demo_export_audit_entry_counts": {},
            "demo_reaction_set_verified_by": None,
            "demo_reaction_set_verified_at": None,
            "issues": [
                "release package parent is not a regular directory: "
                f"{symlink_parent}"
            ],
        }
    package_path = package_path.resolve()
    issues: list[str] = []
    artifact_names: list[str] = []
    source: dict[str, Any] = {}
    demo_ready = None
    demo_export_formats: list[str] = []
    demo_export_audit_entry_counts: dict[str, Any] = {}
    demo_reaction_set_verified_by = None
    demo_reaction_set_verified_at = None
    package_sha256 = None

    if not package_path.exists():
        issues.append(f"release package missing: {package_path}")
        return {
            "ok": False,
            "package_path": str(package_path),
            "package_sha256": package_sha256,
            "artifact_count": 0,
            "artifact_names": artifact_names,
            "source": source,
            "demo_ready": demo_ready,
            "demo_export_formats": demo_export_formats,
            "demo_export_audit_entry_counts": demo_export_audit_entry_counts,
            "demo_reaction_set_verified_by": demo_reaction_set_verified_by,
            "demo_reaction_set_verified_at": demo_reaction_set_verified_at,
            "issues": issues,
        }

    if not package_path.is_file():
        issues.append(f"release package is not a file: {package_path}")
        return {
            "ok": False,
            "package_path": str(package_path),
            "package_sha256": package_sha256,
            "artifact_count": 0,
            "artifact_names": artifact_names,
            "source": source,
            "demo_ready": demo_ready,
            "demo_export_formats": demo_export_formats,
            "demo_export_audit_entry_counts": demo_export_audit_entry_counts,
            "demo_reaction_set_verified_by": demo_reaction_set_verified_by,
            "demo_reaction_set_verified_at": demo_reaction_set_verified_at,
            "issues": issues,
        }

    package_sha256 = sha256_file(package_path)

    expected_names = artifact_filenames()
    try:
        with zipfile.ZipFile(package_path) as archive:
            artifact_names = sorted(archive.namelist())
            if artifact_names != expected_names:
                issues.append(f"release package artifacts mismatch: {artifact_names!r}")
            if len(artifact_names) != len(set(artifact_names)):
                issues.append("release package contains duplicate artifact names")
            unsafe_names = [
                name
                for name in archive.namelist()
                if is_unsafe_archive_name(name)
            ]
            if unsafe_names:
                issues.append(f"release package contains unsafe artifact names: {unsafe_names!r}")

            if not issues:
                with tempfile.TemporaryDirectory(prefix="paper-lab-release-package-") as extract_dir:
                    archive.extractall(extract_dir)
                    validation = validate_release_artifacts(
                        Path(extract_dir).resolve(),
                        require_clean_source=require_clean_source,
                    )
                    source = validation.get("source") or {}
                    demo_ready = validation.get("demo_ready")
                    demo_export_formats = validation.get("demo_export_formats") or []
                    demo_export_audit_entry_counts = validation.get("demo_export_audit_entry_counts") or {}
                    demo_reaction_set_verified_by = validation.get("demo_reaction_set_verified_by")
                    demo_reaction_set_verified_at = validation.get("demo_reaction_set_verified_at")
                    issues.extend(validation.get("issues") or [])
    except zipfile.BadZipFile as exc:
        issues.append(f"release package invalid zip: {exc}")
    except OSError as exc:
        issues.append(f"release package unreadable: {exc}")

    return {
        "ok": not issues,
        "package_path": str(package_path),
        "package_sha256": package_sha256,
        "artifact_count": len(artifact_names),
        "artifact_names": artifact_names,
        "source": source,
        "demo_ready": demo_ready,
        "demo_export_formats": demo_export_formats,
        "demo_export_audit_entry_counts": demo_export_audit_entry_counts,
        "demo_reaction_set_verified_by": demo_reaction_set_verified_by,
        "demo_reaction_set_verified_at": demo_reaction_set_verified_at,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a packaged release handoff zip file.")
    parser.add_argument(
        "--package",
        default="out/paper-lab-agent-release.zip",
        type=Path,
        help="Release zip package path.",
    )
    parser.add_argument(
        "--require-clean-source",
        action="store_true",
        help="Fail when the packaged manifest records a dirty source worktree.",
    )
    parser.add_argument("--compact", action="store_true", help="Emit compact single-line JSON.")
    args = parser.parse_args()

    report = validate_release_package(args.package, require_clean_source=args.require_clean_source)
    print(format_report(report, compact=args.compact))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
