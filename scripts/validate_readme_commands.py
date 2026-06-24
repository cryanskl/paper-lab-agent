#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path


BASH_FENCE_RE = re.compile(r"^```(?:bash|sh|shell)\s*$")
FENCE_RE = re.compile(r"^```")
ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def bash_command_lines(readme_path: Path) -> list[str]:
    lines: list[str] = []
    in_bash_block = False
    for raw_line in readme_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if in_bash_block:
            if FENCE_RE.match(line):
                in_bash_block = False
                continue
            if line and not line.startswith("#"):
                lines.append(line)
            continue
        if BASH_FENCE_RE.match(line):
            in_bash_block = True
    return lines


def split_command(line: str) -> list[str]:
    try:
        return shlex.split(line)
    except ValueError:
        return line.split()


def strip_leading_env_assignments(tokens: list[str]) -> list[str]:
    stripped = list(tokens)
    while stripped and ENV_ASSIGNMENT_RE.match(stripped[0]):
        stripped.pop(0)
    return stripped


def command_targets(readme_path: Path) -> list[str]:
    targets: list[str] = []
    for line in bash_command_lines(readme_path):
        tokens = strip_leading_env_assignments(split_command(line))
        for index, token in enumerate(tokens):
            if token.startswith("scripts/") and token.endswith((".py", ".sh")):
                targets.append(token)
            elif token == "streamlit_app.py":
                targets.append(token)
            elif token == "-m" and index + 1 < len(tokens):
                module = tokens[index + 1]
                if module.startswith("scripts."):
                    targets.append(module.replace(".", "/") + ".py")
    return targets


def missing_command_targets(repo: Path) -> list[str]:
    readme_path = repo / "README.md"
    if not readme_path.exists():
        return ["README.md: missing"]

    issues: list[str] = []
    for target in command_targets(readme_path):
        if not (repo / target).exists():
            issues.append(f"README.md: command target missing: {target}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate local command targets documented in README.md.")
    parser.add_argument("repo", nargs="?", default=".", type=Path)
    args = parser.parse_args()

    issues = missing_command_targets(args.repo)
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
