#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import __version__


EXPECTED_SERVICE = "paper-lab-agent"
EXPECTED_ARTIFACTS = {
    "openapi": "openapi.json",
    "demo_summary": "demo-summary.json",
    "manifest": "release-manifest.json",
}
EXPECTED_EXPORT_FORMATS = ["json", "txt", "bolsig"]
GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_checksum(payload: dict[str, Any]) -> str:
    canonical = json.loads(json.dumps(payload))
    checksums = canonical.get("checksums")
    if isinstance(checksums, dict):
        checksums[EXPECTED_ARTIFACTS["manifest"]] = ""
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path, label: str, issues: list[str]) -> dict[str, Any]:
    if not path.exists():
        issues.append(f"{label} missing: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append(f"{label} invalid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        issues.append(f"{label} must be a JSON object")
        return {}
    return payload


def demo_audit_entry_count_issues(demo_summary: dict[str, Any]) -> list[str]:
    counts = demo_summary.get("export_audit_entry_counts")
    if not isinstance(counts, dict):
        missing = EXPECTED_EXPORT_FORMATS
    else:
        missing = [
            fmt
            for fmt in EXPECTED_EXPORT_FORMATS
            if not isinstance(counts.get(fmt), int) or isinstance(counts.get(fmt), bool) or counts.get(fmt) <= 0
        ]
    if missing:
        return [
            "demo summary export_audit_entry_counts must include positive counts for: "
            + ", ".join(missing)
        ]
    return []


def is_iso8601_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_release_artifacts(artifact_dir: Path, *, require_clean_source: bool = False) -> dict[str, Any]:
    artifact_dir = artifact_dir.resolve()
    issues: list[str] = []
    manifest = read_json(artifact_dir / EXPECTED_ARTIFACTS["manifest"], "release manifest", issues)
    openapi = read_json(artifact_dir / EXPECTED_ARTIFACTS["openapi"], "OpenAPI artifact", issues)
    demo_summary = read_json(artifact_dir / EXPECTED_ARTIFACTS["demo_summary"], "demo summary", issues)

    paths = openapi.get("paths", {}) if isinstance(openapi.get("paths"), dict) else {}
    openapi_path_count = len(paths)
    demo_export_formats = demo_summary.get("export_formats") or []
    demo_export_audit_entry_counts = (
        demo_summary.get("export_audit_entry_counts")
        if isinstance(demo_summary.get("export_audit_entry_counts"), dict)
        else {}
    )
    demo_reaction_set_verified_by = demo_summary.get("reaction_set_verified_by")
    demo_reaction_set_verified_at = demo_summary.get("reaction_set_verified_at")

    if manifest:
        if manifest.get("service") != EXPECTED_SERVICE:
            issues.append(f"release manifest service mismatch: {manifest.get('service')!r}")
        if manifest.get("version") != __version__:
            issues.append(f"release manifest version mismatch: {manifest.get('version')!r}")
        if openapi and manifest.get("version") != openapi.get("info", {}).get("version"):
            issues.append("release manifest version does not match OpenAPI version")
        if manifest.get("artifacts") != EXPECTED_ARTIFACTS:
            issues.append(f"release manifest artifacts mismatch: {manifest.get('artifacts')!r}")
        if manifest.get("demo_ready") is not True:
            issues.append("release manifest demo_ready must be true")
        if manifest.get("demo_export_formats") != EXPECTED_EXPORT_FORMATS:
            issues.append(
                f"release manifest demo_export_formats mismatch: {manifest.get('demo_export_formats')!r}"
            )
        if manifest.get("demo_export_audit_entry_counts") != demo_export_audit_entry_counts:
            issues.append(
                "release manifest demo_export_audit_entry_counts mismatch: "
                f"{manifest.get('demo_export_audit_entry_counts')!r}"
            )
        if manifest.get("demo_reaction_set_verified_by") != demo_reaction_set_verified_by:
            issues.append(
                "release manifest demo_reaction_set_verified_by mismatch: "
                f"{manifest.get('demo_reaction_set_verified_by')!r}"
            )
        if manifest.get("demo_reaction_set_verified_at") != demo_reaction_set_verified_at:
            issues.append(
                "release manifest demo_reaction_set_verified_at mismatch: "
                f"{manifest.get('demo_reaction_set_verified_at')!r}"
            )
        if manifest.get("openapi_path_count") != openapi_path_count:
            issues.append(
                f"release manifest openapi_path_count mismatch: {manifest.get('openapi_path_count')!r}"
            )
        source = manifest.get("source")
        if not isinstance(source, dict):
            issues.append("release manifest source must be an object")
        else:
            git_commit = source.get("git_commit")
            git_branch = source.get("git_branch")
            git_dirty = source.get("git_dirty")
            if not isinstance(git_commit, str) or not GIT_COMMIT_RE.fullmatch(git_commit):
                issues.append(f"release manifest source.git_commit invalid: {git_commit!r}")
            if not isinstance(git_branch, str) or not git_branch.strip():
                issues.append(f"release manifest source.git_branch invalid: {git_branch!r}")
            if not isinstance(git_dirty, bool):
                issues.append(f"release manifest source.git_dirty invalid: {git_dirty!r}")
            if require_clean_source and git_dirty is True:
                issues.append("release manifest source.git_dirty must be false for clean-source validation")
        checksums = manifest.get("checksums")
        if not isinstance(checksums, dict):
            issues.append("release manifest checksums must be an object")
        else:
            expected_checksum_names = set(EXPECTED_ARTIFACTS.values())
            if set(checksums) != expected_checksum_names:
                issues.append(f"release manifest checksums keys mismatch: {sorted(checksums)!r}")
            for artifact_name in (EXPECTED_ARTIFACTS["openapi"], EXPECTED_ARTIFACTS["demo_summary"]):
                artifact_path = artifact_dir / artifact_name
                if artifact_path.exists() and checksums.get(artifact_name) != sha256_file(artifact_path):
                    issues.append(f"checksum mismatch: {artifact_name}")
            if checksums.get(EXPECTED_ARTIFACTS["manifest"]) != manifest_checksum(manifest):
                issues.append(f"checksum mismatch: {EXPECTED_ARTIFACTS['manifest']}")

    if openapi:
        if openapi.get("info", {}).get("title") != EXPECTED_SERVICE:
            issues.append(f"OpenAPI title mismatch: {openapi.get('info', {}).get('title')!r}")
        if "/api/v1/health" not in paths:
            issues.append("OpenAPI missing /api/v1/health")

    if demo_summary:
        if demo_summary.get("ready") is not True:
            issues.append("demo summary ready must be true")
        if demo_export_formats != EXPECTED_EXPORT_FORMATS:
            issues.append(f"demo summary export_formats mismatch: {demo_export_formats!r}")
        issues.extend(demo_audit_entry_count_issues(demo_summary))
        if not isinstance(demo_reaction_set_verified_by, str) or not demo_reaction_set_verified_by.strip():
            issues.append("demo summary reaction_set_verified_by must be a non-empty string")
        if not isinstance(demo_reaction_set_verified_at, str) or not demo_reaction_set_verified_at.strip():
            issues.append("demo summary reaction_set_verified_at must be a non-empty string")
        elif not is_iso8601_timestamp(demo_reaction_set_verified_at):
            issues.append("demo summary reaction_set_verified_at must be an ISO8601 timestamp")

    return {
        "ok": not issues,
        "artifact_dir": str(artifact_dir),
        "service": manifest.get("service"),
        "version": manifest.get("version"),
        "source": manifest.get("source") if isinstance(manifest.get("source"), dict) else {},
        "demo_ready": manifest.get("demo_ready"),
        "demo_export_formats": manifest.get("demo_export_formats") or [],
        "demo_export_audit_entry_counts": manifest.get("demo_export_audit_entry_counts")
        if isinstance(manifest.get("demo_export_audit_entry_counts"), dict)
        else demo_export_audit_entry_counts,
        "demo_reaction_set_verified_by": manifest.get("demo_reaction_set_verified_by")
        or demo_reaction_set_verified_by,
        "demo_reaction_set_verified_at": manifest.get("demo_reaction_set_verified_at")
        or demo_reaction_set_verified_at,
        "openapi_path_count": openapi_path_count,
        "checksums": manifest.get("checksums") if isinstance(manifest.get("checksums"), dict) else {},
        "issues": issues,
    }


def format_report(report: dict[str, Any], *, compact: bool = False) -> str:
    return json.dumps(
        report,
        ensure_ascii=False,
        indent=None if compact else 2,
        separators=(",", ":") if compact else None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a release handoff artifact directory.")
    parser.add_argument("--artifact-dir", default="out/release", type=Path, help="Directory with release artifacts.")
    parser.add_argument(
        "--require-clean-source",
        action="store_true",
        help="Fail when the manifest records a dirty source worktree.",
    )
    parser.add_argument("--compact", action="store_true", help="Emit compact single-line JSON.")
    args = parser.parse_args()

    report = validate_release_artifacts(args.artifact_dir, require_clean_source=args.require_clean_source)
    print(format_report(report, compact=args.compact))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
