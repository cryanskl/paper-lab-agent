#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


BUG_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
REQUIRED_SECTIONS = ("现象", "原因", "修复", "验证")
TEMPLATE_PLACEHOLDER_LABELS = (
    "触发命令、接口或页面",
    "实际结果",
    "期望结果",
    "根因",
    "影响范围",
    "修改文件",
    "关键行为",
    "RED 证据",
    "GREEN 证据",
    "完整 gate",
)


def has_title(text: str) -> bool:
    match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    return bool(match and match.group(1).strip())


def section_body(text: str, section: str) -> str | None:
    match = re.search(rf"^## {re.escape(section)}\s*$", text, flags=re.MULTILINE)
    if match is None:
        return None
    next_match = re.search(r"^##\s+", text[match.end() :], flags=re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    return text[match.end() : end].strip()


def unresolved_template_placeholders(text: str) -> list[str]:
    labels = []
    for label in TEMPLATE_PLACEHOLDER_LABELS:
        pattern = rf"^\s*[-*]\s*{re.escape(label)}[：:]\s*$"
        if re.search(pattern, text, flags=re.MULTILINE):
            labels.append(label)
    return labels


def has_pending_release_gate_evidence(text: str) -> bool:
    return bool(re.search(r"^\s*[-*]\s*完整 gate[：:].*待运行", text, flags=re.MULTILINE))


def has_release_gate_evidence(text: str) -> bool:
    return bool(re.search(r"^\s*[-*]\s*完整 gate[：:]", text, flags=re.MULTILINE))


def has_incomplete_release_gate_evidence(text: str) -> bool:
    for match in re.finditer(r"^\s*[-*]\s*完整 gate[：:](.*)$", text, flags=re.MULTILINE):
        if not re.search(r"\b\d+\s+passed\b", match.group(1)):
            return True
    return False


def first_symlink_parent(path: Path) -> Path | None:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        return parent
    return None


def bug_doc_issues(repo: Path) -> list[str]:
    repo = repo.resolve()
    bug_dir = repo / "docs" / "bug"
    if first_symlink_parent(bug_dir) is not None:
        return ["docs/bug: bug directory parent is not a regular directory"]
    if bug_dir.parent.exists() and not bug_dir.parent.is_dir():
        return ["docs/bug: bug directory parent is not a regular directory"]
    if not bug_dir.exists():
        return ["docs/bug: missing"]
    if bug_dir.is_symlink() or not bug_dir.is_dir():
        return ["docs/bug: bug directory is not a regular directory"]

    issues: list[str] = []
    readme_path = bug_dir / "README.md"
    if not readme_path.exists():
        issues.append("docs/bug/README.md: missing")
    elif readme_path.is_symlink() or not readme_path.is_file():
        issues.append("docs/bug/README.md: bug docs README is not a regular file")

    for path in sorted(bug_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        rel = path.relative_to(repo).as_posix()
        if not BUG_FILENAME_RE.fullmatch(path.name):
            issues.append(f"{rel}: filename must match YYYY-MM-DD-short-slug.md")
        if path.is_symlink() or not path.is_file():
            issues.append(f"{rel}: bug doc is not a regular file")
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            issues.append(f"{rel}: bug doc unreadable")
            continue
        if not has_title(text):
            issues.append(f"{rel}: missing title")
        missing_sections = [
            section for section in REQUIRED_SECTIONS if section_body(text, section) is None
        ]
        if missing_sections:
            issues.append(f"{rel}: missing sections: {', '.join(missing_sections)}")
        empty_sections = [
            section for section in REQUIRED_SECTIONS if section_body(text, section) == ""
        ]
        if empty_sections:
            issues.append(f"{rel}: empty sections: {', '.join(empty_sections)}")
        placeholders = unresolved_template_placeholders(text)
        if placeholders:
            issues.append(
                f"{rel}: unresolved template placeholders: {', '.join(placeholders)}"
            )
        if not has_release_gate_evidence(text):
            issues.append(f"{rel}: missing release gate evidence")
        if has_pending_release_gate_evidence(text):
            issues.append(f"{rel}: pending release gate evidence")
        if has_incomplete_release_gate_evidence(text):
            issues.append(f"{rel}: incomplete release gate evidence")

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
