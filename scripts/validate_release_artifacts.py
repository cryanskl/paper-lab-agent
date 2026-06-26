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

from app import __version__


EXPECTED_SERVICE = "paper-lab-agent"
EXPECTED_ARTIFACTS = {
    "openapi": "openapi.json",
    "demo_summary": "demo-summary.json",
    "manifest": "release-manifest.json",
}
EXPECTED_EXPORT_FORMATS = ["json", "txt", "bolsig"]


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


def validate_release_artifacts(artifact_dir: Path) -> dict[str, Any]:
    artifact_dir = artifact_dir.resolve()
    issues: list[str] = []
    manifest = read_json(artifact_dir / EXPECTED_ARTIFACTS["manifest"], "release manifest", issues)
    openapi = read_json(artifact_dir / EXPECTED_ARTIFACTS["openapi"], "OpenAPI artifact", issues)
    demo_summary = read_json(artifact_dir / EXPECTED_ARTIFACTS["demo_summary"], "demo summary", issues)

    paths = openapi.get("paths", {}) if isinstance(openapi.get("paths"), dict) else {}
    openapi_path_count = len(paths)
    demo_export_formats = demo_summary.get("export_formats") or []

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
        if manifest.get("openapi_path_count") != openapi_path_count:
            issues.append(
                f"release manifest openapi_path_count mismatch: {manifest.get('openapi_path_count')!r}"
            )

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

    return {
        "ok": not issues,
        "artifact_dir": str(artifact_dir),
        "service": manifest.get("service"),
        "version": manifest.get("version"),
        "demo_ready": manifest.get("demo_ready"),
        "demo_export_formats": manifest.get("demo_export_formats") or [],
        "openapi_path_count": openapi_path_count,
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
    parser.add_argument("--compact", action="store_true", help="Emit compact single-line JSON.")
    args = parser.parse_args()

    report = validate_release_artifacts(args.artifact_dir)
    print(format_report(report, compact=args.compact))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
