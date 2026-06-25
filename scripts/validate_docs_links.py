#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
BACKTICK_FILE_RE = re.compile(r"`([^`\s]+\.(?:md|sql))`", re.IGNORECASE)
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.MULTILINE)


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


def clean_link_fragment(target: str) -> str:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if " " in target and not target.startswith("#"):
        target = target.split()[0]
    if "#" not in target:
        return ""
    fragment = target.split("#", 1)[1].split("?", 1)[0]
    return unquote(fragment).strip()


def is_ignored_target(target: str) -> bool:
    lowered = target.lower()
    return not target or target.startswith("#") or lowered.startswith(EXTERNAL_PREFIXES)


def resolve_target_path(repo: Path, source: Path, target: str) -> Path | None:
    target_path = Path(target)
    if target_path.is_absolute():
        return target_path if target_path.exists() else None

    candidates = [
        source.parent / target_path,
        repo / target_path,
        repo / "docs" / target_path,
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def target_exists(repo: Path, source: Path, target: str) -> bool:
    return resolve_target_path(repo, source, target) is not None


def heading_slug(title: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", title.strip().lower())
    text = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"[\s]+", "-", text).strip("-")


def markdown_anchors(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    for match in HEADING_RE.finditer(text):
        slug = heading_slug(match.group(2))
        if not slug:
            continue
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        anchors.add(slug if count == 0 else f"{slug}-{count}")
    return anchors


def anchor_exists(path: Path, fragment: str) -> bool:
    if path.suffix.lower() != ".md":
        return True
    normalized = heading_slug(fragment)
    return bool(normalized and normalized in markdown_anchors(path))


def broken_doc_links(repo: Path) -> list[str]:
    repo = repo.resolve()
    issues: list[str] = []
    for path in doc_files(repo):
        text = path.read_text(encoding="utf-8")
        label = path.relative_to(repo).as_posix()

        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = clean_link_target(raw_target)
            fragment = clean_link_fragment(raw_target)
            if target.lower().startswith(EXTERNAL_PREFIXES):
                continue
            if is_ignored_target(target) and not fragment:
                continue
            target_path = path if not target and fragment else resolve_target_path(repo, path, target)
            if target_path is None:
                issues.append(f"{label}: missing link target {target}")
                continue
            if fragment and not anchor_exists(target_path, fragment):
                target_label = f"{target}#{fragment}" if target else f"#{fragment}"
                issues.append(f"{label}: missing anchor target {target_label}")

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
