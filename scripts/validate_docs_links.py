#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
BACKTICK_FILE_RE = re.compile(
    r"`([^`\s]+\.(?:md|sql|py|sh|ya?ml|example))`",
    re.IGNORECASE,
)
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
    return (
        not target
        or target.startswith("#")
        or lowered.startswith(EXTERNAL_PREFIXES)
        or any(marker in target for marker in "*?[]")
    )


def resolve_target_path(repo: Path, source: Path, target: str) -> Path | None:
    target_path = Path(target)
    if target_path.is_absolute():
        return target_path if target_path.exists() else None

    candidates = target_candidate_paths(repo, source, target)
    return next((candidate for candidate in candidates if candidate.exists()), None)


def target_candidate_paths(repo: Path, source: Path, target: str) -> list[Path]:
    target_path = Path(target)
    if target_path.is_absolute():
        return [target_path]
    return [
        source.parent / target_path,
        repo / target_path,
        repo / "docs" / target_path,
    ]


def target_exists(repo: Path, source: Path, target: str) -> bool:
    return resolve_target_path(repo, source, target) is not None


def is_within_repo(repo: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(repo)
    except ValueError:
        return False
    return True


def heading_slug(title: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", title.strip().lower())
    text = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"[\s]+", "-", text).strip("-")


def markdown_anchors(path: Path) -> set[str] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
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
    anchors = markdown_anchors(path)
    return bool(normalized and anchors is not None and normalized in anchors)


def markdown_file_readable(path: Path) -> bool:
    return path.suffix.lower() != ".md" or markdown_anchors(path) is not None


def first_symlink_parent(path: Path) -> Path | None:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        return parent
    return None


def first_non_directory_parent(path: Path) -> Path | None:
    for parent in path.parents:
        if parent.exists() and not parent.is_dir():
            return parent
    return None


def first_irregular_target_parent(repo: Path, source: Path, target: str) -> Path | None:
    for candidate in target_candidate_paths(repo, source, target):
        symlink_parent = first_symlink_parent(candidate)
        if symlink_parent is not None:
            return symlink_parent
        non_directory_parent = first_non_directory_parent(candidate)
        if non_directory_parent is not None:
            return non_directory_parent
    return None


def broken_doc_links(repo: Path) -> list[str]:
    repo = repo.resolve()
    issues: list[str] = []
    paths = doc_files(repo)
    docs_dir = repo / "docs"
    docs_dir_issue = (
        docs_dir.exists()
        and (docs_dir.is_symlink() or not docs_dir.is_dir())
        and not any(path.is_relative_to(docs_dir) for path in paths)
    )
    for path in paths:
        label = path.relative_to(repo).as_posix()
        if first_symlink_parent(path) is not None:
            issues.append(f"{label}: doc source parent is not a regular directory")
            continue
        if path.is_symlink() or not path.is_file():
            issues.append(f"{label}: doc source is not a regular file")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            issues.append(f"{label}: doc source unreadable")
            continue

        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = clean_link_target(raw_target)
            fragment = clean_link_fragment(raw_target)
            if target.lower().startswith(EXTERNAL_PREFIXES):
                continue
            if is_ignored_target(target) and not fragment:
                continue
            target_path = path if not target and fragment else resolve_target_path(repo, path, target)
            if target_path is None:
                if first_irregular_target_parent(repo, path, target) is not None:
                    issues.append(f"{label}: link target parent is not a regular directory {target}")
                    continue
                issues.append(f"{label}: missing link target {target}")
                continue
            if not is_within_repo(repo, target_path):
                issues.append(f"{label}: link target escapes repository {target}")
                continue
            if first_symlink_parent(target_path) is not None:
                issues.append(f"{label}: link target parent is not a regular directory {target}")
                continue
            if target_path.is_symlink() or not target_path.is_file():
                issues.append(f"{label}: link target is not a regular file {target}")
                continue
            if fragment and not markdown_file_readable(target_path):
                target_label = f"{target}#{fragment}" if target else f"#{fragment}"
                issues.append(f"{label}: link target unreadable {target_label}")
                continue
            if fragment and not anchor_exists(target_path, fragment):
                target_label = f"{target}#{fragment}" if target else f"#{fragment}"
                issues.append(f"{label}: missing anchor target {target_label}")

        for raw_target in BACKTICK_FILE_RE.findall(text):
            target = clean_link_target(raw_target)
            if is_ignored_target(target):
                continue
            target_path = resolve_target_path(repo, path, target)
            if target_path is None:
                if first_irregular_target_parent(repo, path, target) is not None:
                    issues.append(f"{label}: reference target parent is not a regular directory {target}")
                    continue
                issues.append(f"{label}: missing reference target {target}")
                continue
            if not is_within_repo(repo, target_path):
                issues.append(f"{label}: reference target escapes repository {target}")
                continue
            if first_symlink_parent(target_path) is not None:
                issues.append(f"{label}: reference target parent is not a regular directory {target}")
                continue
            if target_path.is_symlink() or not target_path.is_file():
                issues.append(f"{label}: reference target is not a regular file {target}")

    if docs_dir_issue and not any(
        issue.startswith("docs:")
        or issue.startswith("docs/")
        or " docs/" in issue
        for issue in issues
    ):
        issues.append("docs: doc source directory is not a regular directory")

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
