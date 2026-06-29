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
    "acceptance_matrix": "release-acceptance-matrix.md",
    "manifest": "release-manifest.json",
}
EXPECTED_ARTIFACT_NAMES = sorted(EXPECTED_ARTIFACTS.values())
EXPECTED_EXPORT_FORMATS = ["json", "txt", "bolsig"]
EXPECTED_DEMO_COUNT_MINIMUMS = {
    "documents": 1,
    "reaction_audits": 1,
}
EXPECTED_DEMO_WORKFLOW_STATUSES = {
    "parse_status": "parsed",
    "index_status": "indexed",
    "chemistry_status": "extracted",
    "translation_status": "done",
    "reaction_set_status": "verified",
}
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
    if path.is_symlink():
        issues.append(f"{label} is not a regular file: {path}")
        return {}
    if not path.exists():
        issues.append(f"{label} missing: {path}")
        return {}
    if not path.is_file():
        issues.append(f"{label} is not a regular file: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        issues.append(f"{label} unreadable: {exc}")
        return {}
    except json.JSONDecodeError as exc:
        issues.append(f"{label} invalid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        issues.append(f"{label} must be a JSON object")
        return {}
    return payload


def read_text_artifact(path: Path, label: str, issues: list[str]) -> str:
    if path.is_symlink():
        issues.append(f"{label} is not a regular file: {path}")
        return ""
    if not path.exists():
        issues.append(f"{label} missing: {path}")
        return ""
    if not path.is_file():
        issues.append(f"{label} is not a regular file: {path}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        issues.append(f"{label} unreadable: {exc}")
        return ""


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


def demo_audit_summary_format_issues(demo_summary: dict[str, Any]) -> list[str]:
    formats = demo_summary.get("export_audit_summary_formats")
    if formats != EXPECTED_EXPORT_FORMATS:
        return [f"demo summary export_audit_summary_formats mismatch: {formats or []!r}"]
    return []


def demo_count_issues(demo_summary: dict[str, Any]) -> list[str]:
    counts = demo_summary.get("counts")
    if not isinstance(counts, dict):
        missing = list(EXPECTED_DEMO_COUNT_MINIMUMS)
    else:
        missing = [
            key
            for key, minimum in EXPECTED_DEMO_COUNT_MINIMUMS.items()
            if not isinstance(counts.get(key), int)
            or isinstance(counts.get(key), bool)
            or counts.get(key) < minimum
        ]
    if missing:
        return ["demo summary counts must include positive counts for: " + ", ".join(missing)]
    return []


def demo_workflow_statuses(demo_summary: dict[str, Any]) -> dict[str, Any]:
    return {key: demo_summary.get(key) for key in EXPECTED_DEMO_WORKFLOW_STATUSES}


def demo_workflow_status_issues(demo_summary: dict[str, Any]) -> list[str]:
    statuses = demo_workflow_statuses(demo_summary)
    if statuses != EXPECTED_DEMO_WORKFLOW_STATUSES:
        return [f"demo summary workflow statuses mismatch: {statuses!r}"]
    return []


def list_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def first_duplicate_string(values: list[str]) -> str | None:
    seen = set()
    for value in values:
        if value in seen:
            return value
        seen.add(value)
    return None


def warning_details_codes(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    codes = []
    for item in value:
        if not isinstance(item, dict):
            return None
        code = item.get("code")
        capability = item.get("capability")
        message = item.get("message")
        if not isinstance(code, str) or not code.strip():
            return None
        if not isinstance(capability, str) or not capability.strip():
            return None
        if not isinstance(message, str) or not message.strip():
            return None
        codes.append(code)
    return codes


def is_iso8601_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def first_symlink_parent(path: Path) -> Path | None:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        return parent
    return None


def validate_release_artifacts(artifact_dir: Path, *, require_clean_source: bool = False) -> dict[str, Any]:
    requested_artifact_dir = artifact_dir
    if requested_artifact_dir.is_symlink():
        artifact_dir = requested_artifact_dir.absolute()
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir),
            "service": None,
            "version": None,
            "source": {},
            "demo_ready": None,
            "demo_counts": {},
            "demo_workflow_statuses": {},
            "demo_export_formats": [],
            "demo_export_audit_entry_counts": {},
            "demo_export_audit_summary_formats": [],
            "demo_reaction_set_verified_by": None,
            "demo_reaction_set_verified_at": None,
            "openapi_path_count": 0,
            "checksums": {},
            "issues": [f"release artifact directory is not a regular directory: {artifact_dir}"],
        }
    symlink_parent = first_symlink_parent(requested_artifact_dir)
    if symlink_parent is not None:
        artifact_dir = requested_artifact_dir.absolute()
        return {
            "ok": False,
            "artifact_dir": str(artifact_dir),
            "service": None,
            "version": None,
            "source": {},
            "demo_ready": None,
            "demo_counts": {},
            "demo_workflow_statuses": {},
            "demo_export_formats": [],
            "demo_export_audit_entry_counts": {},
            "demo_export_audit_summary_formats": [],
            "demo_reaction_set_verified_by": None,
            "demo_reaction_set_verified_at": None,
            "openapi_path_count": 0,
            "checksums": {},
            "issues": [
                "release artifact directory parent is not a regular directory: "
                f"{symlink_parent}"
            ],
        }
    artifact_dir = artifact_dir.resolve()
    issues: list[str] = []
    if artifact_dir.exists() and not artifact_dir.is_dir():
        issues.append(f"release artifact directory is not a regular directory: {artifact_dir}")
    elif artifact_dir.exists():
        unexpected_files = sorted(
            path.name
            for path in artifact_dir.iterdir()
            if path.name not in EXPECTED_ARTIFACTS.values()
        )
        if unexpected_files:
            issues.append(f"release artifact directory contains unexpected files: {unexpected_files!r}")
    manifest = read_json(artifact_dir / EXPECTED_ARTIFACTS["manifest"], "release manifest", issues)
    openapi = read_json(artifact_dir / EXPECTED_ARTIFACTS["openapi"], "OpenAPI artifact", issues)
    demo_summary = read_json(artifact_dir / EXPECTED_ARTIFACTS["demo_summary"], "demo summary", issues)
    acceptance_matrix = read_text_artifact(
        artifact_dir / EXPECTED_ARTIFACTS["acceptance_matrix"],
        "release acceptance matrix",
        issues,
    )

    paths = openapi.get("paths", {}) if isinstance(openapi.get("paths"), dict) else {}
    openapi_path_count = len(paths)
    openapi_tag_names = {
        tag.get("name")
        for tag in openapi.get("tags", [])
        if isinstance(tag, dict) and isinstance(tag.get("name"), str)
    }
    openapi_schemas = (
        openapi.get("components", {}).get("schemas", {})
        if isinstance(openapi.get("components"), dict)
        and isinstance(openapi.get("components", {}).get("schemas"), dict)
        else {}
    )
    demo_export_formats = demo_summary.get("export_formats") or []
    demo_counts = demo_summary.get("counts") if isinstance(demo_summary.get("counts"), dict) else {}
    demo_statuses = demo_workflow_statuses(demo_summary)
    demo_export_audit_entry_counts = (
        demo_summary.get("export_audit_entry_counts")
        if isinstance(demo_summary.get("export_audit_entry_counts"), dict)
        else {}
    )
    demo_export_audit_summary_formats = demo_summary.get("export_audit_summary_formats") or []
    demo_reaction_set_verified_by = demo_summary.get("reaction_set_verified_by")
    demo_reaction_set_verified_at = demo_summary.get("reaction_set_verified_at")
    preflight_warning_codes = manifest.get("preflight_warning_codes")
    preflight_warning_details = manifest.get("preflight_warning_details")

    if manifest:
        if manifest.get("service") != EXPECTED_SERVICE:
            issues.append(f"release manifest service mismatch: {manifest.get('service')!r}")
        if manifest.get("version") != __version__:
            issues.append(f"release manifest version mismatch: {manifest.get('version')!r}")
        if openapi and manifest.get("version") != openapi.get("info", {}).get("version"):
            issues.append("release manifest version does not match OpenAPI version")
        if manifest.get("artifacts") != EXPECTED_ARTIFACTS:
            issues.append(f"release manifest artifacts mismatch: {manifest.get('artifacts')!r}")
        if "artifact_count" in manifest and manifest.get("artifact_count") != len(EXPECTED_ARTIFACTS):
            issues.append(f"release manifest artifact_count mismatch: {manifest.get('artifact_count')!r}")
        if "artifact_names" in manifest and manifest.get("artifact_names") != EXPECTED_ARTIFACT_NAMES:
            issues.append(f"release manifest artifact_names mismatch: {manifest.get('artifact_names')!r}")
        if manifest.get("demo_ready") is not True:
            issues.append("release manifest demo_ready must be true")
        if manifest.get("demo_counts") != demo_counts:
            issues.append(f"release manifest demo_counts mismatch: {manifest.get('demo_counts')!r}")
        if manifest.get("demo_workflow_statuses") != demo_statuses:
            issues.append(
                "release manifest demo_workflow_statuses mismatch: "
                f"{manifest.get('demo_workflow_statuses')!r}"
            )
        if manifest.get("demo_export_formats") != EXPECTED_EXPORT_FORMATS:
            issues.append(
                f"release manifest demo_export_formats mismatch: {manifest.get('demo_export_formats')!r}"
            )
        if manifest.get("demo_export_audit_entry_counts") != demo_export_audit_entry_counts:
            issues.append(
                "release manifest demo_export_audit_entry_counts mismatch: "
                f"{manifest.get('demo_export_audit_entry_counts')!r}"
            )
        if manifest.get("demo_export_audit_summary_formats") != demo_export_audit_summary_formats:
            issues.append(
                "release manifest demo_export_audit_summary_formats mismatch: "
                f"{manifest.get('demo_export_audit_summary_formats')!r}"
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
        if manifest.get("preflight_ok") is not True:
            issues.append("release manifest preflight_ok must be true")
        if isinstance(manifest.get("preflight_warning_count"), bool) or not isinstance(manifest.get("preflight_warning_count"), int):
            issues.append(
                f"release manifest preflight_warning_count invalid: {manifest.get('preflight_warning_count')!r}"
            )
        elif list_of_strings(preflight_warning_codes) and manifest.get("preflight_warning_count") != len(preflight_warning_codes):
            issues.append(
                "release manifest preflight_warning_count mismatch: "
                f"{manifest.get('preflight_warning_count')!r}"
            )
        if not list_of_strings(preflight_warning_codes):
            issues.append(
                f"release manifest preflight_warning_codes invalid: {preflight_warning_codes!r}"
            )
        else:
            duplicate_code = first_duplicate_string(preflight_warning_codes)
            if duplicate_code is not None:
                issues.append(f"release manifest preflight_warning_codes duplicate: {duplicate_code!r}")
        detail_codes = warning_details_codes(preflight_warning_details)
        if detail_codes is None:
            issues.append("release manifest preflight_warning_details invalid")
        elif list_of_strings(preflight_warning_codes) and detail_codes != preflight_warning_codes:
            issues.append(
                "release manifest preflight_warning_details codes mismatch: "
                f"{detail_codes!r}"
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
            for artifact_name in sorted(name for name in EXPECTED_ARTIFACTS.values() if name != EXPECTED_ARTIFACTS["manifest"]):
                artifact_path = artifact_dir / artifact_name
                if artifact_path.exists() and (artifact_path.is_symlink() or not artifact_path.is_file()):
                    issues.append(f"checksum unavailable: {artifact_name} is not a file: {artifact_path}")
                elif artifact_path.exists() and checksums.get(artifact_name) != sha256_file(artifact_path):
                    issues.append(f"checksum mismatch: {artifact_name}")
            if checksums.get(EXPECTED_ARTIFACTS["manifest"]) != manifest_checksum(manifest):
                issues.append(f"checksum mismatch: {EXPECTED_ARTIFACTS['manifest']}")

    if openapi:
        if openapi.get("info", {}).get("title") != EXPECTED_SERVICE:
            issues.append(f"OpenAPI title mismatch: {openapi.get('info', {}).get('title')!r}")
        if "/api/v1/health" not in paths:
            issues.append("OpenAPI missing /api/v1/health")
        if "system" not in openapi_tag_names:
            issues.append("OpenAPI missing system tag metadata")
        if "ErrorResponse" not in openapi_schemas:
            issues.append("OpenAPI missing ErrorResponse schema")

    if demo_summary:
        if demo_summary.get("ready") is not True:
            issues.append("demo summary ready must be true")
        issues.extend(demo_count_issues(demo_summary))
        issues.extend(demo_workflow_status_issues(demo_summary))
        if demo_export_formats != EXPECTED_EXPORT_FORMATS:
            issues.append(f"demo summary export_formats mismatch: {demo_export_formats!r}")
        issues.extend(demo_audit_entry_count_issues(demo_summary))
        issues.extend(demo_audit_summary_format_issues(demo_summary))
        if not isinstance(demo_reaction_set_verified_by, str) or not demo_reaction_set_verified_by.strip():
            issues.append("demo summary reaction_set_verified_by must be a non-empty string")
        if not isinstance(demo_reaction_set_verified_at, str) or not demo_reaction_set_verified_at.strip():
            issues.append("demo summary reaction_set_verified_at must be a non-empty string")
        elif not is_iso8601_timestamp(demo_reaction_set_verified_at):
            issues.append("demo summary reaction_set_verified_at must be an ISO8601 timestamp")

    if acceptance_matrix:
        for required_text in [
            "Release Acceptance Matrix",
            "docs/PRD_等离子体文献系统.md",
            "docs/接口设计文档.md",
            "docs/schema.sql",
            "bash scripts/release_check.sh",
        ]:
            if required_text not in acceptance_matrix:
                issues.append(f"release acceptance matrix missing text: {required_text}")

    return {
        "ok": not issues,
        "artifact_dir": str(artifact_dir),
        "service": manifest.get("service"),
        "version": manifest.get("version"),
        "source": manifest.get("source") if isinstance(manifest.get("source"), dict) else {},
        "demo_ready": manifest.get("demo_ready"),
        "demo_counts": manifest.get("demo_counts") if isinstance(manifest.get("demo_counts"), dict) else demo_counts,
        "demo_workflow_statuses": manifest.get("demo_workflow_statuses")
        if isinstance(manifest.get("demo_workflow_statuses"), dict)
        else demo_statuses,
        "demo_export_formats": manifest.get("demo_export_formats") or [],
        "demo_export_audit_entry_counts": manifest.get("demo_export_audit_entry_counts")
        if isinstance(manifest.get("demo_export_audit_entry_counts"), dict)
        else demo_export_audit_entry_counts,
        "demo_export_audit_summary_formats": manifest.get("demo_export_audit_summary_formats")
        or demo_export_audit_summary_formats,
        "demo_reaction_set_verified_by": manifest.get("demo_reaction_set_verified_by")
        or demo_reaction_set_verified_by,
        "demo_reaction_set_verified_at": manifest.get("demo_reaction_set_verified_at")
        or demo_reaction_set_verified_at,
        "preflight_ok": manifest.get("preflight_ok"),
        "preflight_warning_count": manifest.get("preflight_warning_count"),
        "preflight_warning_codes": manifest.get("preflight_warning_codes")
        if list_of_strings(manifest.get("preflight_warning_codes"))
        else [],
        "preflight_warning_details": manifest.get("preflight_warning_details")
        if warning_details_codes(manifest.get("preflight_warning_details")) is not None
        else [],
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
