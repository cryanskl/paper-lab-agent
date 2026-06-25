#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


BUG_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
REQUIRED_SECTIONS = ("现象", "原因", "修复", "验证")


def bug_doc_issues(repo: Path) -> list[str]:
    repo = repo.resolve()
    bug_dir = repo / "docs" / "bug"
    if not bug_dir.exists():
        return ["docs/bug: missing"]

    issues: list[str] = []
    if not (bug_dir / "README.md").exists():
        issues.append("docs/bug/README.md: missing")

    for path in sorted(bug_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        rel = path.relative_to(repo).as_posix()
        if not BUG_FILENAME_RE.fullmatch(path.name):
            issues.append(f"{rel}: filename must match YYYY-MM-DD-short-slug.md")

        text = path.read_text(encoding="utf-8")
        missing_sections = [
            section for section in REQUIRED_SECTIONS if f"## {section}" not in text
        ]
        if missing_sections:
            issues.append(f"{rel}: missing sections: {', '.join(missing_sections)}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate docs/bug record files.")
    parser.add_argument("repo", nargs="?", default=".", type=Path)
    args = parser.parse_args()

    issues = bug_doc_issues(args.repo)
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
