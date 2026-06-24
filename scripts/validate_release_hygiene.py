from __future__ import annotations

import argparse
import sys
from pathlib import Path


REQUIRED_GITIGNORE_PATTERNS = [
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
    if REQUIRED_CI_RELEASE_CHECK not in workflow_text:
        return ["ci_runs_release_check"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release hygiene ignore rules.")
    parser.add_argument("gitignore", nargs="?", default=".gitignore", type=Path)
    args = parser.parse_args()

    missing = missing_required_gitignore_patterns(args.gitignore)
    missing_ci = missing_required_ci_release_gate(args.gitignore.parent)
    if missing:
        print(f"gitignore missing patterns: {', '.join(missing)}", file=sys.stderr)
        return 1
    if missing_ci:
        print(f"CI release gate missing: {', '.join(missing_ci)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
