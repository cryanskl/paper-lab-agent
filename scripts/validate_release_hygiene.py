from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path


REQUIRED_GITIGNORE_PATTERNS = [
    ".DS_Store",
    ".env",
    ".venv/",
    "data/",
    ".uv-cache/",
    ".pytest_cache/",
    ".next/",
    "__pycache__/",
]
REQUIRED_CI_WORKFLOW = Path(".github/workflows/ci.yml")
REQUIRED_CI_RELEASE_CHECK = "bash scripts/release_check.sh"
REQUIRED_CI_TRIGGERS = ["push", "pull_request"]
FORBIDDEN_TRACKED_PATTERNS = [
    ".DS_Store",
    "*/.DS_Store",
    ".env",
    ".env.local",
    ".env.*.local",
    ".env.development",
    ".env.production",
    "data/*",
    "*.db",
    "*.sqlite",
    "*.sqlite-shm",
    "*.sqlite-wal",
    "__pycache__/*",
    "*.pyc",
    ".pytest_cache/*",
    ".uv-cache/*",
    "coverage/*",
    "test-results/*",
    "playwright-report/*",
]


def load_gitignore_patterns(path: Path) -> set[str]:
    patterns: set[str] = set()
    if not path.exists():
        return patterns
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.add(line)
    return patterns


def missing_required_gitignore_patterns(path: Path) -> list[str]:
    patterns = load_gitignore_patterns(path)
    return [pattern for pattern in REQUIRED_GITIGNORE_PATTERNS if pattern not in patterns]


def missing_required_ci_release_gate(repo: Path) -> list[str]:
    workflow_path = repo / REQUIRED_CI_WORKFLOW
    if not workflow_path.exists():
        return ["ci_workflow"]
    workflow_text = workflow_path.read_text(encoding="utf-8")
    missing = []
    for trigger in REQUIRED_CI_TRIGGERS:
        if f"\n  {trigger}:" not in workflow_text and f"\n  - {trigger}" not in workflow_text:
            missing.append(f"ci_{trigger}_trigger")
    if REQUIRED_CI_RELEASE_CHECK not in workflow_text:
        missing.append("ci_runs_release_check")
    return missing


def forbidden_tracked_paths(paths: list[str]) -> list[str]:
    forbidden: list[str] = []
    for path in paths:
        normalized = path.replace("\\", "/").strip()
        if not normalized:
            continue
        if any(fnmatch.fnmatch(normalized, pattern) for pattern in FORBIDDEN_TRACKED_PATTERNS):
            forbidden.append(path)
    return forbidden


def tracked_files(repo: Path) -> list[str]:
    git_dir = repo / ".git"
    if not git_dir.exists():
        return []
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release hygiene ignore rules.")
    parser.add_argument("gitignore", nargs="?", default=".gitignore", type=Path)
    args = parser.parse_args()

    repo = args.gitignore.parent
    missing = missing_required_gitignore_patterns(args.gitignore)
    missing_ci = missing_required_ci_release_gate(repo)
    forbidden = forbidden_tracked_paths(tracked_files(repo))
    if missing:
        print(f"gitignore missing patterns: {', '.join(missing)}", file=sys.stderr)
        return 1
    if missing_ci:
        print(f"CI release gate missing: {', '.join(missing_ci)}", file=sys.stderr)
        return 1
    if forbidden:
        print(f"forbidden tracked files: {', '.join(forbidden)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
