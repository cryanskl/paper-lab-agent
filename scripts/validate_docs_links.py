#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
BACKTICK_FILE_RE = re.compile(r"`([^`\s]+\.(?:md|sql))`", re.IGNORECASE)
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")


def doc_files(repo: Path) -> list[Path]:
    candidates = [repo / "README.md", repo / "AGENTS.md", repo / "CLAUDE.md"]
    docs_dir = repo / "docs"
    if docs_dir.exists():
        candidates.extend(sorted(docs_dir.rglob("*.md")))
    return [path for path in candidates if path.exists()]


def clean_link_target(target: str) -> str:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if " " in target and not target.startswith("#"):
        target = target.split()[0]
    target = target.split("#", 1)[0].split("?", 1)[0]
    return target


def is_ignored_target(target: str) -> bool:
    lowered = target.lower()
    return not target or target.startswith("#") or lowered.startswith(EXTERNAL_PREFIXES)


def target_exists(repo: Path, source: Path, target: str) -> bool:
    target_path = Path(target)
    if target_path.is_absolute():
        return target_path.exists()

    candidates = [
        source.parent / target_path,
        repo / target_path,
        repo / "docs" / target_path,
    ]
    return any(candidate.exists() for candidate in candidates)


def broken_doc_links(repo: Path) -> list[str]:
    repo = repo.resolve()
    issues: list[str] = []
    for path in doc_files(repo):
        text = path.read_text(encoding="utf-8")
        label = path.relative_to(repo).as_posix()

        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = clean_link_target(raw_target)
            if is_ignored_target(target):
                continue
            if not target_exists(repo, path, target):
                issues.append(f"{label}: missing link target {target}")

        for raw_target in BACKTICK_FILE_RE.findall(text):
            target = clean_link_target(raw_target)
            if is_ignored_target(target):
                continue
            if not target_exists(repo, path, target):
                issues.append(f"{label}: missing reference target {target}")

    return issues


def main() -> int:
    repo = Path.cwd()
    issues = broken_doc_links(repo)
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
