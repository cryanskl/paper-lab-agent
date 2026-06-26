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

from scripts.validate_release_artifacts import EXPECTED_ARTIFACTS, format_report, validate_release_artifacts


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_filenames() -> list[str]:
    return sorted(EXPECTED_ARTIFACTS.values())


def package_release_artifacts(
    artifact_dir: Path,
    output_path: Path,
    *,
    require_clean_source: bool = False,
) -> dict[str, Any]:
    artifact_dir = artifact_dir.resolve()
    output_path = output_path.resolve()
    validation = validate_release_artifacts(artifact_dir, require_clean_source=require_clean_source)
    if validation.get("ok") is not True:
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir),
            "package_path": str(output_path),
            "artifact_count": 0,
            "artifact_names": [],
            "package_sha256": None,
            "source": validation.get("source") or {},
            "demo_ready": validation.get("demo_ready"),
            "demo_export_formats": validation.get("demo_export_formats") or [],
            "demo_export_audit_entry_counts": validation.get("demo_export_audit_entry_counts") or {},
            "issues": validation.get("issues") or ["release artifact validation failed"],
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename in artifact_filenames():
            archive.write(artifact_dir / filename, arcname=filename)

    return {
        "ok": True,
        "artifact_dir": str(artifact_dir),
        "package_path": str(output_path),
        "artifact_count": len(artifact_filenames()),
        "artifact_names": artifact_filenames(),
        "package_sha256": sha256_file(output_path),
        "source": validation.get("source") or {},
        "demo_ready": validation.get("demo_ready"),
        "demo_export_formats": validation.get("demo_export_formats") or [],
        "demo_export_audit_entry_counts": validation.get("demo_export_audit_entry_counts") or {},
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
