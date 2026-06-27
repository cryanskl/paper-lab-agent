#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import importlib.util
import re
import shlex
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse


BASH_FENCE_RE = re.compile(r"^```(?:bash|sh|shell)\s*$")
FENCE_RE = re.compile(r"^```")
ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
LOCAL_COMMANDS = {"bash", "curl", "python", "python3", "pip", "source", "uvicorn"}
LOCAL_CURL_HOSTS = {"127.0.0.1", "localhost", "::1"}
HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}
UVICORN_OPTIONS_WITH_VALUES = {
    "--app-dir",
    "--backlog",
    "--env-file",
    "--fd",
    "--forwarded-allow-ips",
    "--h11-max-incomplete-event-size",
    "--header",
    "--host",
    "--lifespan",
    "--limit-concurrency",
    "--limit-max-requests",
    "--log-config",
    "--log-level",
    "--loop",
    "--port",
    "--reload-delay",
    "--reload-dir",
    "--reload-exclude",
    "--reload-include",
    "--root-path",
    "--ssl-ca-certs",
    "--ssl-cert-reqs",
    "--ssl-certfile",
    "--ssl-ciphers",
    "--ssl-keyfile",
    "--timeout-graceful-shutdown",
    "--timeout-keep-alive",
    "--uds",
    "--workers",
    "--ws",
    "--ws-max-queue",
    "--ws-max-size",
    "--ws-ping-interval",
    "--ws-ping-timeout",
    "--ws-per-message-deflate",
}
UVICORN_FLAG_OPTIONS = {"--date-header", "--factory", "--proxy-headers", "--server-header", "--use-colors"}


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
            command = tokens[0].removeprefix("./") if tokens else ""
            if command and (command in LOCAL_COMMANDS or command.startswith("scripts/")):
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
            script_target = token.removeprefix("./")
            if script_target.startswith("scripts/") and script_target.endswith((".py", ".sh")):
                targets.append(script_target)
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
                script = tokens[index + 1].removeprefix("./")
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


def safe_python_script_target(repo: Path, script: str) -> bool:
    script_path = repo / script
    return (
        script_path.exists()
        and is_within_repo(repo, script_path)
        and first_symlink_parent(script_path) is None
        and not script_path.is_symlink()
        and script_path.is_file()
    )


def is_within_repo(repo: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(repo.resolve())
    except ValueError:
        return False
    return True


@contextmanager
def repo_on_sys_path(repo: Path):
    repo_path = str(repo.resolve())
    inserted = False
    if repo_path not in sys.path:
        sys.path.insert(0, repo_path)
        inserted = True
    importlib.invalidate_caches()
    try:
        yield
    finally:
        if inserted:
            try:
                sys.path.remove(repo_path)
            except ValueError:
                pass
        importlib.invalidate_caches()


@contextmanager
def isolated_module_cache(module_name: str):
    names = [".".join(module_name.split(".")[:index]) for index in range(1, len(module_name.split(".")) + 1)]
    saved = {name: sys.modules[name] for name in names if name in sys.modules}
    for name in reversed(names):
        sys.modules.pop(name, None)
    try:
        yield
    finally:
        for name in reversed(names):
            sys.modules.pop(name, None)
        sys.modules.update(saved)


def local_module_path(repo: Path, module_name: str) -> Path | None:
    parts = module_name.split(".")
    module_file = repo.joinpath(*parts).with_suffix(".py")
    package_init = repo.joinpath(*parts, "__init__.py")
    for candidate in [module_file, package_init]:
        if candidate.exists():
            return candidate
    return None


def top_level_names(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                names.update(assigned_names(target))
        elif isinstance(node, ast.AnnAssign):
            names.update(assigned_names(node.target))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".", 1)[0])
    return names


def assigned_names(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in node.elts:
            names.update(assigned_names(element))
        return names
    return set()


def local_uvicorn_target_issue(repo: Path, module_name: str, attribute_path: str, target: str, label: str) -> str | None:
    module_path = local_module_path(repo, module_name)
    if module_path is None:
        return None
    if not is_within_repo(repo, module_path):
        return f"{label}: uvicorn target outside repository: {target}"
    if first_symlink_parent(module_path) is not None or module_path.is_symlink() or not module_path.is_file():
        return f"{label}: uvicorn target missing: {target}"
    if "." in attribute_path:
        return f"{label}: uvicorn target missing: {target}"
    attribute = attribute_path.split(".", 1)[0]
    if attribute not in top_level_names(module_path):
        return f"{label}: uvicorn target missing: {target}"
    return ""


def uvicorn_app_refs(readme_path: Path) -> list[str]:
    refs: list[str] = []
    for line in command_lines(readme_path):
        tokens = strip_leading_env_assignments(split_command(line))
        if not tokens:
            continue
        if tokens[0] == "uvicorn":
            option_tokens = tokens[1:]
        elif len(tokens) >= 4 and tokens[0] in {"python", "python3"} and tokens[1] == "-m" and tokens[2] == "uvicorn":
            option_tokens = tokens[3:]
        else:
            continue
        skip_next = False
        for token in option_tokens:
            if skip_next:
                skip_next = False
                continue
            if token.startswith("-"):
                option_name = token.split("=", 1)[0]
                if option_name in UVICORN_FLAG_OPTIONS:
                    continue
                if option_name in UVICORN_OPTIONS_WITH_VALUES and "=" not in token:
                    skip_next = True
                continue
            if ":" in token:
                refs.append(token)
                break
    return refs


def uvicorn_target_issue(repo: Path, target: str, label: str) -> str | None:
    if ":" not in target:
        return f"{label}: uvicorn target missing: {target}"
    module_name, attribute_path = target.rsplit(":", 1)
    if not module_name or not attribute_path:
        return f"{label}: uvicorn target missing: {target}"
    local_issue = local_uvicorn_target_issue(repo, module_name, attribute_path, target, label)
    if local_issue is not None:
        return None if local_issue == "" else local_issue
    with repo_on_sys_path(repo), isolated_module_cache(module_name):
        try:
            spec = importlib.util.find_spec(module_name)
        except ModuleNotFoundError:
            spec = None
        if spec is None or spec.origin is None:
            return f"{label}: uvicorn target missing: {target}"
        if spec.origin not in {"built-in", "frozen"} and not is_within_repo(repo, Path(spec.origin)):
            return f"{label}: uvicorn target outside repository: {target}"
        try:
            module = __import__(module_name, fromlist=["*"])
        except Exception:
            return f"{label}: uvicorn target missing: {target}"
    current = module
    for attribute in attribute_path.split("."):
        if not hasattr(current, attribute):
            return f"{label}: uvicorn target missing: {target}"
        current = getattr(current, attribute)
    return None


def missing_uvicorn_targets(readme_path: Path) -> list[str]:
    repo = readme_path.parent
    return [
        issue
        for target in uvicorn_app_refs(readme_path)
        if (issue := uvicorn_target_issue(repo, target, "README.md")) is not None
    ]


def missing_uvicorn_targets_for_doc(repo: Path, doc_path: Path, label: str) -> list[str]:
    return [
        issue
        for target in uvicorn_app_refs(doc_path)
        if (issue := uvicorn_target_issue(repo, target, label)) is not None
    ]


def missing_python_script_options_for_doc(repo: Path, doc_path: Path, label: str) -> list[str]:
    issues: list[str] = []
    help_cache: dict[str, str | None] = {}
    for script, option in python_script_option_refs(doc_path):
        if not safe_python_script_target(repo, script):
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
            issues.append(f"{label}: option {option} not found in {script} --help")
    return issues


def missing_python_script_options(repo: Path, readme_path: Path) -> list[str]:
    return missing_python_script_options_for_doc(repo, readme_path, "README.md")


def command_doc_paths(repo: Path) -> list[tuple[Path, str]]:
    docs = [(repo / "README.md", "README.md")]
    release_checklist = repo / "docs" / "release-checklist.md"
    if release_checklist.exists():
        docs.append((release_checklist, "docs/release-checklist.md"))
    return docs


def first_symlink_parent(path: Path) -> Path | None:
    for parent in path.parents:
        if not parent.is_symlink():
            continue
        if parent.is_absolute() and parent.parent == Path(parent.anchor):
            continue
        return parent
    return None


def missing_command_targets_for_doc(repo: Path, doc_path: Path, label: str) -> list[str]:
    if first_symlink_parent(doc_path) is not None:
        return [f"{label}: command doc parent is not a regular directory"]
    if doc_path.is_symlink() or not doc_path.is_file():
        return [f"{label}: command doc is not a regular file"]

    issues: list[str] = []
    for target in command_targets(doc_path):
        target_path = repo / target
        if not target_path.exists():
            issues.append(f"{label}: command target missing: {target}")
            continue
        if not is_within_repo(repo, target_path):
            issues.append(f"{label}: command target escapes repository: {target}")
            continue
        if first_symlink_parent(target_path) is not None:
            issues.append(f"{label}: command target parent is not a regular directory: {target}")
            continue
        if target_path.is_symlink() or not target_path.is_file():
            issues.append(f"{label}: command target is not a regular file: {target}")
    issues.extend(missing_python_script_options_for_doc(repo, doc_path, label))
    issues.extend(missing_uvicorn_targets_for_doc(repo, doc_path, label))
    actual_routes = app_routes()
    for method, path in documented_local_curl_routes(doc_path):
        if (method, path) not in actual_routes:
            issues.append(f"{label}: curl route missing: {method} {path}")
    return issues


def missing_command_targets(repo: Path) -> list[str]:
    readme_path = repo / "README.md"
    if not readme_path.exists():
        return ["README.md: missing"]

    issues: list[str] = []
    for doc_path, label in command_doc_paths(repo):
        issues.extend(missing_command_targets_for_doc(repo, doc_path, label))
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
