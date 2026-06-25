#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


BASH_FENCE_RE = re.compile(r"^```(?:bash|sh|shell)\s*$")
FENCE_RE = re.compile(r"^```")
ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
LOCAL_COMMANDS = {"bash", "curl", "python", "python3", "pip", "source"}
LOCAL_CURL_HOSTS = {"127.0.0.1", "localhost", "::1"}
HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


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


def inline_command_lines(readme_path: Path) -> list[str]:
    lines: list[str] = []
    in_code_block = False
    for raw_line in readme_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if FENCE_RE.match(line):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        for match in INLINE_CODE_RE.finditer(raw_line):
            candidate = match.group(1).strip()
            tokens = strip_leading_env_assignments(split_command(candidate))
            if tokens and (tokens[0] in LOCAL_COMMANDS or tokens[0].startswith("scripts/")):
                lines.append(candidate)
    return lines


def command_lines(readme_path: Path) -> list[str]:
    return [*bash_command_lines(readme_path), *inline_command_lines(readme_path)]


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


def normalize_route_path(path: str) -> str:
    value = path.strip().split("?", 1)[0].rstrip("/")
    if not value.startswith("/"):
        value = f"/{value}"
    return re.sub(r"\{[^}/]+\}", "{}", value)


def app_routes() -> set[tuple[str, str]]:
    from app.main import app

    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods:
            continue
        normalized_path = normalize_route_path(str(path))
        for method in methods:
            method = method.upper()
            if method in HTTP_METHODS:
                routes.add((method, normalized_path))
    return routes


def curl_method(tokens: list[str]) -> str:
    method = "GET"
    for index, token in enumerate(tokens):
        if token in {"-X", "--request"} and index + 1 < len(tokens):
            candidate = tokens[index + 1].upper()
            if candidate in HTTP_METHODS:
                method = candidate
    return method


def curl_url(tokens: list[str]) -> str | None:
    for token in tokens[1:]:
        if token.startswith(("http://", "https://")):
            return token
    return None


def documented_local_curl_routes(readme_path: Path) -> list[tuple[str, str]]:
    routes: list[tuple[str, str]] = []
    for line in command_lines(readme_path):
        tokens = strip_leading_env_assignments(split_command(line))
        if not tokens or tokens[0] != "curl":
            continue
        url = curl_url(tokens)
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.hostname not in LOCAL_CURL_HOSTS:
            continue
        routes.append((curl_method(tokens), normalize_route_path(parsed.path)))
    return routes


def command_targets(readme_path: Path) -> list[str]:
    targets: list[str] = []
    for line in command_lines(readme_path):
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


def python_script_option_refs(readme_path: Path) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for line in command_lines(readme_path):
        tokens = strip_leading_env_assignments(split_command(line))
        if not tokens:
            continue
        for index, token in enumerate(tokens):
            if token in {"python", "python3"} and index + 1 < len(tokens):
                script = tokens[index + 1]
                option_tokens = tokens[index + 2 :]
            elif token == "-m" and index > 0 and tokens[index - 1] in {"python", "python3"} and index + 1 < len(tokens):
                module = tokens[index + 1]
                if not module.startswith("scripts."):
                    continue
                script = module.replace(".", "/") + ".py"
                option_tokens = tokens[index + 2 :]
            else:
                continue
            if not script.startswith("scripts/") or not script.endswith(".py"):
                continue
            for option in option_tokens:
                if option.startswith("--"):
                    refs.append((script, option.split("=", 1)[0]))
    return refs


def missing_python_script_options(repo: Path, readme_path: Path) -> list[str]:
    issues: list[str] = []
    help_cache: dict[str, str | None] = {}
    for script, option in python_script_option_refs(readme_path):
        script_path = repo / script
        if not script_path.exists():
            continue
        if script not in help_cache:
            result = subprocess.run(
                [sys.executable, script, "--help"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            help_cache[script] = result.stdout + result.stderr if result.returncode == 0 else None
        help_text = help_cache[script]
        if help_text is not None and option not in help_text:
            issues.append(f"README.md: option {option} not found in {script} --help")
    return issues


def missing_command_targets(repo: Path) -> list[str]:
    readme_path = repo / "README.md"
    if not readme_path.exists():
        return ["README.md: missing"]

    issues: list[str] = []
    for target in command_targets(readme_path):
        if not (repo / target).exists():
            issues.append(f"README.md: command target missing: {target}")
    issues.extend(missing_python_script_options(repo, readme_path))
    actual_routes = app_routes()
    for method, path in documented_local_curl_routes(readme_path):
        if (method, path) not in actual_routes:
            issues.append(f"README.md: curl route missing: {method} {path}")
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
