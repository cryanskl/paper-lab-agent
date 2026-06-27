import json
import re
import string
import zipfile
from pathlib import Path


def load_validate_env_example():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_env_example.py"
    spec = importlib.util.spec_from_file_location("validate_env_example_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_env_example = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_env_example)
    return validate_env_example


def load_doctor():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("doctor_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)
    return doctor


def load_validate_release_hygiene():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_release_hygiene.py"
    spec = importlib.util.spec_from_file_location("validate_release_hygiene_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_release_hygiene = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_release_hygiene)
    return validate_release_hygiene


def load_validate_api_contract():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_api_contract.py"
    spec = importlib.util.spec_from_file_location("validate_api_contract_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_api_contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_api_contract)
    return validate_api_contract


def load_validate_schema():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_schema.py"
    spec = importlib.util.spec_from_file_location("validate_schema_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_schema = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_schema)
    return validate_schema


def load_validate_requirements():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_requirements.py"
    spec = importlib.util.spec_from_file_location("validate_requirements_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_requirements = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_requirements)
    return validate_requirements


def load_validate_docs_links():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_docs_links.py"
    spec = importlib.util.spec_from_file_location("validate_docs_links_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_docs_links = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_docs_links)
    return validate_docs_links


def load_validate_readme_commands():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_readme_commands.py"
    spec = importlib.util.spec_from_file_location("validate_readme_commands_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_readme_commands = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_readme_commands)
    return validate_readme_commands


def load_smoke_check():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "smoke_check.py"
    spec = importlib.util.spec_from_file_location("smoke_check_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    smoke_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke_check)
    return smoke_check


def load_export_openapi():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "export_openapi.py"
    spec = importlib.util.spec_from_file_location("export_openapi_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    export_openapi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(export_openapi)
    return export_openapi


def load_export_release_artifacts():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "export_release_artifacts.py"
    spec = importlib.util.spec_from_file_location("export_release_artifacts_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    export_release_artifacts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(export_release_artifacts)
    return export_release_artifacts


def load_validate_release_artifacts():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_release_artifacts.py"
    spec = importlib.util.spec_from_file_location("validate_release_artifacts_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_release_artifacts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_release_artifacts)
    return validate_release_artifacts


def load_package_release_artifacts():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "package_release_artifacts.py"
    spec = importlib.util.spec_from_file_location("package_release_artifacts_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    package_release_artifacts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(package_release_artifacts)
    return package_release_artifacts


def load_validate_release_package():
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_release_package.py"
    spec = importlib.util.spec_from_file_location("validate_release_package_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_release_package = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_release_package)
    return validate_release_package


def test_env_example_contains_required_external_dependency_keys():
    validate_env_example = load_validate_env_example()
    env_path = Path(__file__).resolve().parent.parent / ".env.example"

    missing = validate_env_example.missing_required_keys(env_path)

    assert missing == []


def test_env_example_validator_reports_missing_required_key(tmp_path):
    validate_env_example = load_validate_env_example()
    repo = Path(__file__).resolve().parent.parent
    env_path = tmp_path / ".env.example"
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_path.write_text(env_text.replace("VECTOR_DB_PATH=./data/vector-index.json\n", ""), encoding="utf-8")

    missing = validate_env_example.missing_required_keys(env_path)

    assert missing == ["VECTOR_DB_PATH"]


def test_env_example_validator_reports_missing_settings_alias(tmp_path):
    validate_env_example = load_validate_env_example()
    repo = Path(__file__).resolve().parent.parent
    env_path = tmp_path / ".env.example"
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_path.write_text(env_text.replace("LLM_BASE_URL=https://api.openai.com/v1\n", ""), encoding="utf-8")

    missing = validate_env_example.missing_required_keys(env_path)

    assert missing == ["LLM_BASE_URL"]


def test_env_example_validator_reports_missing_script_runtime_key(tmp_path):
    validate_env_example = load_validate_env_example()
    repo = Path(__file__).resolve().parent.parent
    env_path = tmp_path / ".env.example"
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_path.write_text(env_text.replace("FRONTEND_URL=http://127.0.0.1:8501\n", ""), encoding="utf-8")

    missing = validate_env_example.missing_required_keys(env_path)

    assert missing == ["FRONTEND_URL"]


def test_env_example_keeps_secret_like_values_blank():
    validate_env_example = load_validate_env_example()
    env_path = Path(__file__).resolve().parent.parent / ".env.example"

    filled = validate_env_example.non_empty_secret_like_keys(env_path)

    assert filled == []


def test_env_example_defaults_match_settings_defaults():
    validate_env_example = load_validate_env_example()
    repo = Path(__file__).resolve().parent.parent

    mismatches = validate_env_example.documented_default_mismatches(repo / ".env.example")

    assert mismatches == []


def test_env_example_validator_reports_default_drift(tmp_path):
    validate_env_example = load_validate_env_example()
    repo = Path(__file__).resolve().parent.parent
    env_path = tmp_path / ".env.example"
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_path.write_text(env_text.replace("LLM_MODEL=gpt-4o-mini\n", "LLM_MODEL=legacy-model\n"), encoding="utf-8")

    mismatches = validate_env_example.documented_default_mismatches(env_path)

    assert mismatches == ["LLM_MODEL expected gpt-4o-mini, got legacy-model"]


def test_env_example_validator_reports_dev_ready_timeout_drift(tmp_path):
    validate_env_example = load_validate_env_example()
    repo = Path(__file__).resolve().parent.parent
    env_path = tmp_path / ".env.example"
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_path.write_text(env_text.replace("DEV_READY_TIMEOUT=30\n", "DEV_READY_TIMEOUT=10\n"), encoding="utf-8")

    mismatches = validate_env_example.script_runtime_default_mismatches(env_path)

    assert mismatches == ["DEV_READY_TIMEOUT expected 30, got 10"]


def test_env_example_validator_reports_filled_secret_like_values(tmp_path):
    validate_env_example = load_validate_env_example()
    repo = Path(__file__).resolve().parent.parent
    env_path = tmp_path / ".env.example"
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_path.write_text(env_text.replace("LLM_API_KEY=\n", "LLM_API_KEY=sk-test\n"), encoding="utf-8")

    filled = validate_env_example.non_empty_secret_like_keys(env_path)

    assert filled == ["LLM_API_KEY"]


def test_gitignore_contains_required_release_hygiene_patterns():
    validate_release_hygiene = load_validate_release_hygiene()
    gitignore_path = Path(__file__).resolve().parent.parent / ".gitignore"

    missing = validate_release_hygiene.missing_required_gitignore_patterns(gitignore_path)

    assert missing == []


def test_release_hygiene_validator_accepts_current_tracked_files():
    import subprocess

    validate_release_hygiene = load_validate_release_hygiene()
    repo = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )

    forbidden = validate_release_hygiene.forbidden_tracked_paths(result.stdout.splitlines())

    assert forbidden == []


def test_release_hygiene_validator_reports_missing_gitignore_pattern(tmp_path):
    validate_release_hygiene = load_validate_release_hygiene()
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text(".env\n.venv/\ndata/\n__pycache__/\n", encoding="utf-8")

    missing = validate_release_hygiene.missing_required_gitignore_patterns(gitignore_path)

    assert ".DS_Store" in missing
    assert ".coverage" in missing
    assert ".coverage.*" in missing
    assert "htmlcov/" in missing
    assert "build/" in missing
    assert "dist/" in missing
    assert "node_modules/" in missing
    assert "out/" in missing
    assert "*.sqlite" in missing
    assert "*.log" in missing
    assert "tsconfig.tsbuildinfo" in missing
    assert "npm-debug.log*" in missing
    assert "pnpm-debug.log*" in missing
    assert "yarn-debug.log*" in missing
    assert "yarn-error.log*" in missing
    assert ".turbo/" in missing
    assert ".cache/" in missing
    assert "coverage/" in missing
    assert "test-results/" in missing
    assert "playwright-report/" in missing
    assert "*.db-wal" in missing
    assert "*.db-shm" in missing
    assert "*.db-journal" in missing
    assert "*.sqlite-journal" in missing
    assert ".mypy_cache/" in missing
    assert ".ruff_cache/" in missing
    assert ".next/" in missing


def test_bug_doc_validator_reports_missing_title(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_bug_docs.py"
    spec = importlib.util.spec_from_file_location("validate_bug_docs_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_bug_docs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_bug_docs)

    bug_dir = tmp_path / "docs" / "bug"
    bug_dir.mkdir(parents=True)
    (bug_dir / "README.md").write_text("# Bug 记录约定\n", encoding="utf-8")
    (bug_dir / "2026-06-26-missing-title.md").write_text(
        "## 现象\n\n- observed\n\n## 原因\n\n- reason\n\n## 修复\n\n- fix\n\n## 验证\n\n- test\n",
        encoding="utf-8",
    )

    issues = validate_bug_docs.bug_doc_issues(tmp_path)

    assert "docs/bug/2026-06-26-missing-title.md: missing title" in issues


def test_bug_doc_validator_reports_unresolved_template_placeholders(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_bug_docs.py"
    spec = importlib.util.spec_from_file_location("validate_bug_docs_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_bug_docs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_bug_docs)

    bug_dir = tmp_path / "docs" / "bug"
    bug_dir.mkdir(parents=True)
    (bug_dir / "README.md").write_text("# Bug 记录约定\n", encoding="utf-8")
    (bug_dir / "2026-06-26-template-leftovers.md").write_text(
        "# Template leftovers\n\n"
        "## 现象\n\n"
        "- 触发命令、接口或页面：\n"
        "- 实际结果：\n"
        "- 期望结果：\n\n"
        "## 原因\n\n"
        "- 根因：\n"
        "- 影响范围：\n\n"
        "## 修复\n\n"
        "- 修改文件：\n"
        "- 关键行为：\n\n"
        "## 验证\n\n"
        "- RED 证据：\n"
        "- GREEN 证据：\n"
        "- 完整 gate：\n",
        encoding="utf-8",
    )

    issues = validate_bug_docs.bug_doc_issues(tmp_path)

    assert (
        "docs/bug/2026-06-26-template-leftovers.md: unresolved template placeholders: "
        "触发命令、接口或页面, 实际结果, 期望结果, 根因, 影响范围, 修改文件, "
        "关键行为, RED 证据, GREEN 证据, 完整 gate"
    ) in issues


def test_bug_doc_validator_reports_pending_release_gate_evidence(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_bug_docs.py"
    spec = importlib.util.spec_from_file_location("validate_bug_docs_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_bug_docs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_bug_docs)

    bug_dir = tmp_path / "docs" / "bug"
    bug_dir.mkdir(parents=True)
    (bug_dir / "README.md").write_text("# Bug 记录约定\n", encoding="utf-8")
    (bug_dir / "2026-06-26-pending-gate.md").write_text(
        "# Pending gate\n\n"
        "## 现象\n\n"
        "- observed\n\n"
        "## 原因\n\n"
        "- reason\n\n"
        "## 修复\n\n"
        "- fix\n\n"
        "## 验证\n\n"
        "- RED 证据：failed first\n"
        "- GREEN 证据：target test passed\n"
        "- 完整 gate：待运行 `bash scripts/release_check.sh`。\n",
        encoding="utf-8",
    )

    issues = validate_bug_docs.bug_doc_issues(tmp_path)

    assert (
        "docs/bug/2026-06-26-pending-gate.md: pending release gate evidence"
    ) in issues


def test_bug_doc_validator_reports_release_gate_without_passed_count(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_bug_docs.py"
    spec = importlib.util.spec_from_file_location("validate_bug_docs_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_bug_docs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_bug_docs)

    bug_dir = tmp_path / "docs" / "bug"
    bug_dir.mkdir(parents=True)
    (bug_dir / "README.md").write_text("# Bug 记录约定\n", encoding="utf-8")
    (bug_dir / "2026-06-26-no-gate-count.md").write_text(
        "# Missing gate count\n\n"
        "## 现象\n\n"
        "- observed\n\n"
        "## 原因\n\n"
        "- reason\n\n"
        "## 修复\n\n"
        "- fix\n\n"
        "## 验证\n\n"
        "- RED 证据：failed first\n"
        "- GREEN 证据：target test passed\n"
        "- 完整 gate：`bash scripts/release_check.sh`\n",
        encoding="utf-8",
    )

    issues = validate_bug_docs.bug_doc_issues(tmp_path)

    assert (
        "docs/bug/2026-06-26-no-gate-count.md: incomplete release gate evidence"
    ) in issues


def test_bug_doc_validator_reports_missing_release_gate_evidence(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_bug_docs.py"
    spec = importlib.util.spec_from_file_location("validate_bug_docs_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_bug_docs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_bug_docs)

    bug_dir = tmp_path / "docs" / "bug"
    bug_dir.mkdir(parents=True)
    (bug_dir / "README.md").write_text("# Bug 记录约定\n", encoding="utf-8")
    (bug_dir / "2026-06-26-missing-gate.md").write_text(
        "# Missing gate evidence\n\n"
        "## 现象\n\n"
        "- observed\n\n"
        "## 原因\n\n"
        "- reason\n\n"
        "## 修复\n\n"
        "- fix\n\n"
        "## 验证\n\n"
        "- RED 证据：failed first\n"
        "- GREEN 证据：target test passed\n",
        encoding="utf-8",
    )

    issues = validate_bug_docs.bug_doc_issues(tmp_path)

    assert (
        "docs/bug/2026-06-26-missing-gate.md: missing release gate evidence"
    ) in issues


def test_bug_doc_validator_rejects_symlinked_bug_doc(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_bug_docs.py"
    spec = importlib.util.spec_from_file_location("validate_bug_docs_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_bug_docs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_bug_docs)

    bug_dir = tmp_path / "docs" / "bug"
    bug_dir.mkdir(parents=True)
    (bug_dir / "README.md").write_text("# Bug 记录约定\n", encoding="utf-8")
    outside_path = tmp_path / "outside-bug.md"
    outside_path.write_text(
        "# Outside bug\n\n"
        "## 现象\n\n"
        "- observed\n\n"
        "## 原因\n\n"
        "- reason\n\n"
        "## 修复\n\n"
        "- fix\n\n"
        "## 验证\n\n"
        "- 完整 gate：`bash scripts/release_check.sh` 通过，`776 passed`。\n",
        encoding="utf-8",
    )
    linked_bug = bug_dir / "2026-06-27-linked-bug.md"
    linked_bug.symlink_to(outside_path)

    issues = validate_bug_docs.bug_doc_issues(tmp_path)

    assert (
        "docs/bug/2026-06-27-linked-bug.md: bug doc is not a regular file"
    ) in issues


def test_bug_doc_validator_rejects_symlinked_bug_dir(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_bug_docs.py"
    spec = importlib.util.spec_from_file_location("validate_bug_docs_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_bug_docs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_bug_docs)

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    outside_bug_dir = tmp_path / "outside-bug"
    outside_bug_dir.mkdir()
    (outside_bug_dir / "README.md").write_text("# Outside bug docs\n", encoding="utf-8")
    (outside_bug_dir / "2026-06-27-outside-bug.md").write_text(
        "# Outside bug\n\n"
        "## 现象\n\n"
        "- observed\n\n"
        "## 原因\n\n"
        "- reason\n\n"
        "## 修复\n\n"
        "- fix\n\n"
        "## 验证\n\n"
        "- 完整 gate：`bash scripts/release_check.sh` 通过，`777 passed`。\n",
        encoding="utf-8",
    )
    (docs_dir / "bug").symlink_to(outside_bug_dir, target_is_directory=True)

    issues = validate_bug_docs.bug_doc_issues(tmp_path)

    assert issues == ["docs/bug: bug directory is not a regular directory"]


def test_bug_doc_validator_rejects_symlinked_readme(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "validate_bug_docs.py"
    spec = importlib.util.spec_from_file_location("validate_bug_docs_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    validate_bug_docs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate_bug_docs)

    bug_dir = tmp_path / "docs" / "bug"
    bug_dir.mkdir(parents=True)
    outside_readme = tmp_path / "outside-readme.md"
    outside_readme.write_text("# Outside bug policy\n", encoding="utf-8")
    (bug_dir / "README.md").symlink_to(outside_readme)

    issues = validate_bug_docs.bug_doc_issues(tmp_path)

    assert "docs/bug/README.md: bug docs README is not a regular file" in issues


def test_release_hygiene_validator_reports_tracked_generated_artifacts():
    validate_release_hygiene = load_validate_release_hygiene()

    forbidden = validate_release_hygiene.forbidden_tracked_paths(
        [
            "README.md",
            ".env",
            ".DS_Store",
            "docs/.DS_Store",
            ".next/app-build-manifest.json",
            "node_modules/react/index.js",
            "out/index.html",
            ".coverage",
            ".coverage.worker-1",
            "app.log",
            "logs/dev.log",
            "tsconfig.tsbuildinfo",
            "npm-debug.log",
            "pnpm-debug.log",
            "yarn-debug.log",
            "yarn-error.log",
            ".turbo/cache/state.json",
            ".cache/tool/state.json",
            "htmlcov/index.html",
            "build/lib/app/main.py",
            "dist/paper_lab_agent-0.1.0.tar.gz",
            "test-results/e2e.json",
            "playwright-report/index.html",
            "plasma.db-wal",
            "plasma.db-shm",
            "plasma.db-journal",
            "archive.sqlite-journal",
            ".mypy_cache/3.11/app.meta.json",
            ".ruff_cache/0.8.0/123456789",
            "data/plasma.db",
            "scripts/__pycache__/smoke_check.cpython-313.pyc",
            "coverage/index.html",
        ]
    )

    assert forbidden == [
        ".env",
        ".DS_Store",
        "docs/.DS_Store",
        ".next/app-build-manifest.json",
        "node_modules/react/index.js",
        "out/index.html",
        ".coverage",
        ".coverage.worker-1",
        "app.log",
        "logs/dev.log",
        "tsconfig.tsbuildinfo",
        "npm-debug.log",
        "pnpm-debug.log",
        "yarn-debug.log",
        "yarn-error.log",
        ".turbo/cache/state.json",
        ".cache/tool/state.json",
        "htmlcov/index.html",
        "build/lib/app/main.py",
        "dist/paper_lab_agent-0.1.0.tar.gz",
        "test-results/e2e.json",
        "playwright-report/index.html",
        "plasma.db-wal",
        "plasma.db-shm",
        "plasma.db-journal",
        "archive.sqlite-journal",
        ".mypy_cache/3.11/app.meta.json",
        ".ruff_cache/0.8.0/123456789",
        "data/plasma.db",
        "scripts/__pycache__/smoke_check.cpython-313.pyc",
        "coverage/index.html",
    ]


def test_release_hygiene_validator_requires_ci_release_gate():
    validate_release_hygiene = load_validate_release_hygiene()
    repo = Path(__file__).resolve().parent.parent

    missing = validate_release_hygiene.missing_required_ci_release_gate(repo)

    assert missing == []


def test_release_hygiene_validator_reports_missing_ci_release_gate(tmp_path):
    validate_release_hygiene = load_validate_release_hygiene()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "name: ci\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: pytest\n",
        encoding="utf-8",
    )

    missing = validate_release_hygiene.missing_required_ci_release_gate(tmp_path)

    assert "ci_runs_release_check" in missing


def test_release_hygiene_validator_reports_missing_ci_timeout(tmp_path):
    validate_release_hygiene = load_validate_release_hygiene()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "name: ci\non: [push, pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: bash scripts/release_check.sh\n",
        encoding="utf-8",
    )

    missing = validate_release_hygiene.missing_required_ci_release_gate(tmp_path)

    assert "ci_timeout_minutes" in missing


def test_release_hygiene_validator_reports_missing_ci_requirements_install(tmp_path):
    validate_release_hygiene = load_validate_release_hygiene()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "name: ci\n"
        "on: [push, pull_request, workflow_dispatch]\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-latest\n"
        "    timeout-minutes: 15\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - run: bash scripts/release_check.sh\n",
        encoding="utf-8",
    )

    missing = validate_release_hygiene.missing_required_ci_release_gate(tmp_path)

    assert "ci_installs_requirements" in missing


def test_release_hygiene_validator_reports_missing_ci_python_setup(tmp_path):
    validate_release_hygiene = load_validate_release_hygiene()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "name: ci\n"
        "on: [push, pull_request, workflow_dispatch]\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-latest\n"
        "    timeout-minutes: 15\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - run: python -m pip install -r requirements.txt\n"
        "      - run: bash scripts/release_check.sh\n",
        encoding="utf-8",
    )

    missing = validate_release_hygiene.missing_required_ci_release_gate(tmp_path)

    assert "ci_sets_up_python" in missing


def test_release_hygiene_validator_reports_missing_ci_python_version(tmp_path):
    validate_release_hygiene = load_validate_release_hygiene()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "name: ci\n"
        "on: [push, pull_request, workflow_dispatch]\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-latest\n"
        "    timeout-minutes: 15\n"
        "    steps:\n"
        "      - uses: actions/setup-python@v5\n"
        "      - run: python -m pip install -r requirements.txt\n"
        "      - run: bash scripts/release_check.sh\n",
        encoding="utf-8",
    )

    missing = validate_release_hygiene.missing_required_ci_release_gate(tmp_path)

    assert "ci_python_version" in missing


def test_release_hygiene_validator_reports_missing_ci_checkout(tmp_path):
    validate_release_hygiene = load_validate_release_hygiene()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "name: ci\n"
        "on: [push, pull_request, workflow_dispatch]\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-latest\n"
        "    timeout-minutes: 15\n"
        "    steps:\n"
        "      - uses: actions/setup-python@v5\n"
        "        with:\n"
        "          python-version: \"3.11\"\n"
        "      - run: python -m pip install -r requirements.txt\n"
        "      - run: bash scripts/release_check.sh\n",
        encoding="utf-8",
    )

    missing = validate_release_hygiene.missing_required_ci_release_gate(tmp_path)

    assert "ci_checks_out_repo" in missing


def test_release_hygiene_validator_requires_ci_push_and_pull_request_triggers():
    validate_release_hygiene = load_validate_release_hygiene()
    repo = Path(__file__).resolve().parent.parent

    missing = validate_release_hygiene.missing_required_ci_release_gate(repo)

    assert missing == []


def test_release_hygiene_validator_accepts_inline_ci_triggers(tmp_path):
    validate_release_hygiene = load_validate_release_hygiene()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "name: ci\n"
        "on: [push, pull_request, workflow_dispatch]\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: ubuntu-latest\n"
        "    timeout-minutes: 15\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - uses: actions/setup-python@v5\n"
        "        with:\n"
        "          python-version: \"3.11\"\n"
        "      - run: python -m pip install -r requirements.txt\n"
        "      - run: bash scripts/release_check.sh\n",
        encoding="utf-8",
    )

    missing = validate_release_hygiene.missing_required_ci_release_gate(tmp_path)

    assert missing == []


def test_release_hygiene_validator_reports_missing_ci_pull_request_trigger(tmp_path):
    validate_release_hygiene = load_validate_release_hygiene()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "name: ci\n\non:\n  push:\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: bash scripts/release_check.sh\n",
        encoding="utf-8",
    )

    missing = validate_release_hygiene.missing_required_ci_release_gate(tmp_path)

    assert "ci_pull_request_trigger" in missing


def test_release_hygiene_validator_reports_missing_ci_workflow_dispatch_trigger(tmp_path):
    validate_release_hygiene = load_validate_release_hygiene()
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "name: ci\n\non:\n  push:\n  pull_request:\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    timeout-minutes: 15\n    steps:\n      - run: bash scripts/release_check.sh\n",
        encoding="utf-8",
    )

    missing = validate_release_hygiene.missing_required_ci_release_gate(tmp_path)

    assert "ci_workflow_dispatch_trigger" in missing


def test_agent_guides_truth_source_references_point_to_existing_files():
    repo = Path(__file__).resolve().parent.parent
    truth_source_names = {
        "PRD_等离子体文献系统.md",
        "schema.sql",
        "接口设计文档.md",
        "任务拆分_开发路线.md",
    }

    references = []
    missing = []
    for guide_name in ["AGENTS.md", "CLAUDE.md"]:
        guide_text = (repo / guide_name).read_text(encoding="utf-8")
        guide_references = [
            reference
            for reference in re.findall(r"`([^`]+)`", guide_text)
            if Path(reference).name in truth_source_names
        ]
        references.extend((guide_name, reference) for reference in guide_references)
        missing.extend(
            (guide_name, reference) for reference in guide_references if not (repo / reference).exists()
        )

    assert references
    assert missing == []


def test_readme_documents_current_runtime_version():
    repo = Path(__file__).resolve().parent.parent
    namespace: dict[str, str] = {}
    exec((repo / "app" / "__init__.py").read_text(encoding="utf-8"), namespace)
    readme = (repo / "README.md").read_text(encoding="utf-8")

    assert f"当前版本：`{namespace['__version__']}`" in readme


def test_readme_documents_openapi_export_command():
    repo = Path(__file__).resolve().parent.parent
    readme = (repo / "README.md").read_text(encoding="utf-8")

    assert "python scripts/export_openapi.py --output out/openapi.json" in readme
    assert "不启动服务" in readme


def test_ci_workflow_runs_bounded_release_gate():
    repo = Path(__file__).resolve().parent.parent
    workflow = (repo / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "bash scripts/release_check.sh" in workflow
    assert "timeout-minutes: 15" in workflow


def test_readme_documents_manual_ci_release_gate():
    repo = Path(__file__).resolve().parent.parent
    readme = (repo / "README.md").read_text(encoding="utf-8")

    assert "workflow_dispatch" in readme
    assert "GitHub Actions" in readme
    assert "手动触发" in readme


def test_release_checklist_documents_publish_gates():
    repo = Path(__file__).resolve().parent.parent
    readme = (repo / "README.md").read_text(encoding="utf-8")
    checklist_path = repo / "docs" / "release-checklist.md"

    assert "[docs/release-checklist.md](docs/release-checklist.md)" in readme
    checklist = checklist_path.read_text(encoding="utf-8")
    for required in [
        "bash scripts/release_check.sh",
        "python scripts/prepare_demo_data.py --summary-only --compact",
        "python scripts/health_check.py --summary-only --compact",
        "python scripts/health_check.py --require-release-ready",
        "python scripts/health_check.py --require-frontend",
        "python scripts/health_check.py --require-grobid",
        "python scripts/export_openapi.py --output out/openapi.json",
        "python scripts/export_release_artifacts.py --output-dir out/release --compact",
        "workflow_dispatch",
    ]:
        assert required in checklist


def test_release_checklist_documents_git_safety_checks():
    repo = Path(__file__).resolve().parent.parent
    checklist = (repo / "docs" / "release-checklist.md").read_text(encoding="utf-8")

    for required in [
        "git branch --show-current",
        "git rev-parse --show-toplevel",
        "git status --short",
        "git diff --check",
    ]:
        assert required in checklist


def test_doctor_script_reports_missing_required_project_files(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("doctor_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)

    (tmp_path / "scripts").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "requirements.txt").write_text("fastapi==0.1\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("DATABASE_PATH=\n", encoding="utf-8")

    payload = doctor.run_checks(tmp_path)

    assert payload["ok"] is False
    missing = {
        issue["path"]
        for check in payload["checks"]
        for issue in check.get("issues", [])
        if issue.get("code") == "missing_required_file"
    }
    assert "docs/schema.sql" in missing
    assert "scripts/dev.sh" in missing
    assert "streamlit_app.py" in missing


def test_doctor_env_example_check_matches_required_runtime_keys(tmp_path):
    doctor = load_doctor()
    validate_env_example = load_validate_env_example()
    repo = Path(__file__).resolve().parent.parent
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_path = tmp_path / ".env.example"

    for key in validate_env_example.required_env_keys():
        env_path.write_text(
            re.sub(rf"^{re.escape(key)}=.*\n?", "", env_text, flags=re.MULTILINE),
            encoding="utf-8",
        )

        check = doctor.check_env_example(tmp_path)

        assert {
            "code": "missing_env_example_key",
            "key": key,
            "message": f".env.example must document {key}",
        } in check["issues"]


def test_doctor_env_example_check_ignores_comments_and_similar_key_names(tmp_path):
    doctor = load_doctor()
    repo = Path(__file__).resolve().parent.parent
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_text = re.sub(
        r"^OPENALEX_MAILTO=.*$",
        "MY_OPENALEX_MAILTO=lab@example.test",
        env_text,
        flags=re.MULTILINE,
    )
    env_text = re.sub(
        r"^UNPAYWALL_EMAIL=.*$",
        "# UNPAYWALL_EMAIL=ops@example.test",
        env_text,
        flags=re.MULTILINE,
    )
    (tmp_path / ".env.example").write_text(env_text, encoding="utf-8")

    check = doctor.check_env_example(tmp_path)
    missing_keys = [issue.get("key") for issue in check["issues"]]

    assert missing_keys == ["OPENALEX_MAILTO", "UNPAYWALL_EMAIL"]


def test_doctor_env_example_check_rejects_secret_like_values(tmp_path):
    doctor = load_doctor()
    repo = Path(__file__).resolve().parent.parent
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_text = env_text.replace("LLM_API_KEY=\n", "LLM_API_KEY=sk-test\n")
    (tmp_path / ".env.example").write_text(env_text, encoding="utf-8")

    check = doctor.check_env_example(tmp_path)

    assert {
        "code": "non_empty_env_example_secret",
        "key": "LLM_API_KEY",
        "message": ".env.example must leave LLM_API_KEY blank",
    } in check["issues"]


def test_doctor_env_example_check_rejects_settings_default_drift(tmp_path):
    doctor = load_doctor()
    repo = Path(__file__).resolve().parent.parent
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_text = env_text.replace("LLM_MODEL=gpt-4o-mini\n", "LLM_MODEL=legacy-model\n")
    (tmp_path / ".env.example").write_text(env_text, encoding="utf-8")

    check = doctor.check_env_example(tmp_path)

    assert {
        "code": "env_example_default_drift",
        "key": "LLM_MODEL",
        "expected": "gpt-4o-mini",
        "actual": "legacy-model",
        "message": ".env.example LLM_MODEL must match default gpt-4o-mini",
    } in check["issues"]


def test_doctor_env_example_check_rejects_api_base_url_runtime_drift(tmp_path):
    doctor = load_doctor()
    repo = Path(__file__).resolve().parent.parent
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_text = env_text.replace("API_PORT=8000\n", "API_PORT=9000\n")
    (tmp_path / ".env.example").write_text(env_text, encoding="utf-8")

    check = doctor.check_env_example(tmp_path)

    assert {
        "code": "env_example_runtime_default_drift",
        "key": "API_BASE_URL",
        "expected": "http://127.0.0.1:9000/api/v1",
        "actual": "http://127.0.0.1:8000/api/v1",
        "message": ".env.example API_BASE_URL must match runtime default http://127.0.0.1:9000/api/v1",
    } in check["issues"]


def test_doctor_env_example_check_rejects_frontend_url_runtime_drift(tmp_path):
    doctor = load_doctor()
    repo = Path(__file__).resolve().parent.parent
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_text = env_text.replace("STREAMLIT_PORT=8501\n", "STREAMLIT_PORT=9501\n")
    (tmp_path / ".env.example").write_text(env_text, encoding="utf-8")

    check = doctor.check_env_example(tmp_path)

    assert {
        "code": "env_example_runtime_default_drift",
        "key": "FRONTEND_URL",
        "expected": "http://127.0.0.1:9501",
        "actual": "http://127.0.0.1:8501",
        "message": ".env.example FRONTEND_URL must match runtime default http://127.0.0.1:9501",
    } in check["issues"]


def test_doctor_env_example_check_rejects_dev_ready_timeout_runtime_drift(tmp_path):
    doctor = load_doctor()
    repo = Path(__file__).resolve().parent.parent
    env_text = (repo / ".env.example").read_text(encoding="utf-8")
    env_text = env_text.replace("DEV_READY_TIMEOUT=30\n", "DEV_READY_TIMEOUT=10\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "dev.sh").write_text(
        'DEV_READY_TIMEOUT="${DEV_READY_TIMEOUT:-30}"\n',
        encoding="utf-8",
    )
    (tmp_path / ".env.example").write_text(env_text, encoding="utf-8")

    check = doctor.check_env_example(tmp_path)

    assert {
        "code": "env_example_runtime_default_drift",
        "key": "DEV_READY_TIMEOUT",
        "expected": "30",
        "actual": "10",
        "message": ".env.example DEV_READY_TIMEOUT must match runtime default 30",
    } in check["issues"]


def test_doctor_script_reports_missing_python_dependencies(monkeypatch):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("doctor_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)

    def fake_find_spec(name):
        if name == "fastapi":
            return None
        return object()

    monkeypatch.setattr(doctor.importlib.util, "find_spec", fake_find_spec)

    check = doctor.check_python_dependencies()

    assert check["status"] == "fail"
    assert {
        "code": "missing_python_dependency",
        "package": "fastapi",
        "import_name": "fastapi",
        "message": "Python dependency fastapi is not importable as fastapi",
    } in check["issues"]


def test_doctor_script_reports_local_storage_preflight_paths(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("doctor_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)

    project = tmp_path / "project"
    project.mkdir()
    data_dir = tmp_path / "local-data"

    check = doctor.check_local_storage(project, env={"PAPER_LAB_DATA_DIR": str(data_dir)})

    assert check["name"] == "local_storage"
    assert check["status"] == "pass"
    assert check["issues"] == []
    assert check["paths"]["data_dir"] == str(data_dir)
    assert check["paths"]["database_parent"] == str(data_dir)
    assert check["paths"]["pdf_dir"] == str(data_dir / "pdfs")
    assert check["paths"]["vector_db_parent"] == str(data_dir)
    assert data_dir.exists()


def test_doctor_script_reports_storage_parent_that_is_not_directory(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("doctor_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)

    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("file blocks database parent", encoding="utf-8")

    check = doctor.check_local_storage(
        repo,
        env={
            "PAPER_LAB_DATA_DIR": str(tmp_path / "data"),
            "DATABASE_PATH": str(blocked_parent / "plasma.db"),
        },
    )

    assert check["status"] == "fail"
    assert {
        "code": "storage_path_not_directory",
        "key": "database_parent",
        "path": str(blocked_parent),
        "message": f"database_parent must be a writable directory: {blocked_parent}",
    } in check["issues"]


def test_doctor_script_rejects_symlinked_local_storage_dir(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("doctor_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)

    outside_dir = tmp_path / "outside-pdfs"
    outside_dir.mkdir()
    linked_pdf_dir = tmp_path / "pdfs"
    linked_pdf_dir.symlink_to(outside_dir, target_is_directory=True)

    check = doctor.check_local_storage(
        repo,
        env={
            "PAPER_LAB_DATA_DIR": str(tmp_path / "data"),
            "PAPER_LAB_PDF_DIR": str(linked_pdf_dir),
        },
    )

    assert check["status"] == "fail"
    assert {
        "code": "storage_path_not_directory",
        "key": "pdf_dir",
        "path": str(linked_pdf_dir),
        "message": f"pdf_dir must be a writable directory: {linked_pdf_dir}",
    } in check["issues"]
    assert not (outside_dir / ".paper-lab-doctor-write-test").exists()


def test_doctor_script_rejects_symlinked_local_storage_parent(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("doctor_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)

    outside_dir = tmp_path / "outside-storage"
    outside_dir.mkdir()
    linked_root = tmp_path / "linked-root"
    linked_root.symlink_to(outside_dir, target_is_directory=True)
    pdf_dir = linked_root / "pdfs"

    check = doctor.check_local_storage(
        repo,
        env={
            "PAPER_LAB_DATA_DIR": str(tmp_path / "data"),
            "PAPER_LAB_PDF_DIR": str(pdf_dir),
        },
    )

    assert check["status"] == "fail"
    assert {
        "code": "storage_path_not_directory",
        "key": "pdf_dir",
        "path": str(pdf_dir),
        "message": f"pdf_dir must be a writable directory: {pdf_dir}",
    } in check["issues"]
    assert not (outside_dir / "pdfs").exists()


def test_doctor_script_rejects_symlinked_database_path(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("doctor_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)

    outside_db = tmp_path / "outside.db"
    outside_db.write_text("external database", encoding="utf-8")
    linked_db = tmp_path / "plasma.db"
    linked_db.symlink_to(outside_db)

    check = doctor.check_local_storage(
        repo,
        env={
            "PAPER_LAB_DATA_DIR": str(tmp_path / "data"),
            "DATABASE_PATH": str(linked_db),
        },
    )

    assert check["status"] == "fail"
    assert {
        "code": "storage_path_not_file",
        "key": "database_path",
        "path": str(linked_db),
        "message": f"database_path must be a regular file path: {linked_db}",
    } in check["issues"]


def test_doctor_script_rejects_symlinked_vector_db_path(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("doctor_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)

    outside_vector = tmp_path / "outside-vector-index.json"
    outside_vector.write_text("[]", encoding="utf-8")
    linked_vector = tmp_path / "vector-index.json"
    linked_vector.symlink_to(outside_vector)

    check = doctor.check_local_storage(
        repo,
        env={
            "PAPER_LAB_DATA_DIR": str(tmp_path / "data"),
            "VECTOR_DB_PATH": str(linked_vector),
        },
    )

    assert check["status"] == "fail"
    assert {
        "code": "storage_path_not_file",
        "key": "vector_db_path",
        "path": str(linked_vector),
        "message": f"vector_db_path must be a regular file path: {linked_vector}",
    } in check["issues"]


def test_doctor_script_local_storage_preflight_reads_env_file(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("doctor_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)

    project = tmp_path / "project"
    project.mkdir()
    blocked_parent = project / "not-a-directory"
    blocked_parent.write_text("file blocks database parent", encoding="utf-8")
    (project / ".env").write_text(
        "\n".join(
            [
                "PAPER_LAB_DATA_DIR=env-data",
                f"DATABASE_PATH={blocked_parent}/plasma.db",
            ]
        ),
        encoding="utf-8",
    )

    check = doctor.check_local_storage(project, env={})

    assert check["status"] == "fail"
    assert check["paths"]["data_dir"] == str(project / "env-data")
    assert any(
        issue.get("code") == "storage_path_not_directory"
        and issue.get("key") == "database_parent"
        and issue.get("path") == str(blocked_parent)
        for issue in check["issues"]
    )


def test_doctor_script_local_storage_preflight_keeps_environment_override(tmp_path):
    import importlib.util

    repo = Path(__file__).resolve().parent.parent
    script_path = repo / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("doctor_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    doctor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(doctor)

    project = tmp_path / "project"
    project.mkdir()
    (project / ".env").write_text("PAPER_LAB_DATA_DIR=env-data\n", encoding="utf-8")
    override_data_dir = tmp_path / "override-data"

    check = doctor.check_local_storage(project, env={"PAPER_LAB_DATA_DIR": str(override_data_dir)})

    assert check["status"] == "pass"
    assert check["paths"]["data_dir"] == str(override_data_dir)
    assert check["paths"]["pdf_dir"] == str(override_data_dir / "pdfs")


def test_doctor_preflight_is_documented_and_in_release_gate():
    repo = Path(__file__).resolve().parent.parent
    readme = (repo / "README.md").read_text(encoding="utf-8")
    checklist = (repo / "docs" / "release-checklist.md").read_text(encoding="utf-8")
    release_check = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert "python scripts/doctor.py --compact" in readme
    assert "python scripts/doctor.py --strict --compact" in readme
    assert "本地存储目录可创建和可写" in readme
    assert "读取 `.env`" in readme
    assert "python scripts/doctor.py --strict --compact" in checklist
    assert "local storage paths are creatable and writable" in checklist
    assert "reads `.env`" in checklist
    assert "scripts/doctor.py" in release_check
    assert "scripts/doctor.py --help" in release_check
    assert "scripts/doctor.py --strict --compact" in release_check


def test_release_check_compiles_application_package():
    repo = Path(__file__).resolve().parent.parent
    release_check = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert "-m compileall" in release_check
    assert " app " in release_check or " app\n" in release_check


def test_release_check_validates_openapi_export_script():
    repo = Path(__file__).resolve().parent.parent
    release_check = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert "scripts/export_openapi.py" in release_check
    assert "scripts/export_openapi.py --help" in release_check


def test_release_check_validates_release_artifact_bundle():
    repo = Path(__file__).resolve().parent.parent
    release_check = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")
    readme = (repo / "README.md").read_text(encoding="utf-8")
    checklist = (repo / "docs" / "release-checklist.md").read_text(encoding="utf-8")

    assert "scripts/export_release_artifacts.py" in release_check
    assert "scripts/export_release_artifacts.py --help" in release_check
    assert "scripts/package_release_artifacts.py" in release_check
    assert "scripts/package_release_artifacts.py --help" in release_check
    assert "scripts/validate_release_package.py" in release_check
    assert "scripts/validate_release_package.py --help" in release_check
    assert "scripts/validate_release_artifacts.py" in release_check
    assert "scripts/validate_release_artifacts.py --help" in release_check
    assert "RELEASE_ARTIFACTS_JSON" in release_check
    assert "release-manifest.json" in release_check
    assert "demo-summary.json" in release_check
    assert "openapi.json" in release_check
    assert 'package.get("artifact_names") != ["demo-summary.json", "openapi.json", "release-manifest.json"]' in release_check
    assert 'package.get("demo_ready") is not True' in release_check
    assert 'package.get("demo_export_formats") != ["json", "txt", "bolsig"]' in release_check
    assert 'package.get("demo_export_audit_entry_counts") != {"json": 1, "txt": 1, "bolsig": 1}' in release_check
    assert 'package.get("demo_reaction_set_verified_by") != "prepare-demo-data"' in release_check
    assert 'not package.get("demo_reaction_set_verified_at")' in release_check
    assert 'package_validation.get("demo_ready") is not True' in release_check
    assert 'package_validation.get("demo_export_formats") != ["json", "txt", "bolsig"]' in release_check
    assert 'package_validation.get("demo_export_audit_entry_counts") != {"json": 1, "txt": 1, "bolsig": 1}' in release_check
    assert 'package_validation.get("demo_reaction_set_verified_by") != "prepare-demo-data"' in release_check
    assert 'not package_validation.get("demo_reaction_set_verified_at")' in release_check
    assert "release manifest version does not match OpenAPI version" in release_check
    assert "checksums" in release_check
    assert "git_dirty" in release_check
    assert "python scripts/export_release_artifacts.py --output-dir out/release --compact" in readme
    assert "python scripts/validate_release_artifacts.py --artifact-dir out/release --compact" in readme
    assert "--require-clean-source" in readme
    assert "python scripts/package_release_artifacts.py --artifact-dir out/release --output out/paper-lab-agent-release.zip --compact" in readme
    assert "python scripts/validate_release_package.py --package out/paper-lab-agent-release.zip --compact" in readme
    assert "artifact_names" in readme
    assert "reaction_set_verified_by" in readme
    assert "reaction_set_verified_at" in readme
    assert "artifact 路径本身是否为目录" in readme
    assert "是否可读取" in readme
    assert "额外文件" in readme
    assert "zip 输出路径必须放在 artifact 目录外" in readme
    assert "system` tag metadata" in readme
    assert "ErrorResponse` schema" in readme
    assert "python scripts/export_release_artifacts.py --output-dir out/release --compact" in checklist
    assert "python scripts/validate_release_artifacts.py --artifact-dir out/release --compact" in checklist
    assert "python scripts/package_release_artifacts.py --artifact-dir out/release --output out/paper-lab-agent-release.zip --compact" in checklist
    assert "python scripts/validate_release_package.py --package out/paper-lab-agent-release.zip --compact" in checklist
    assert "artifact_names" in checklist
    assert "reaction_set_verified_by" in checklist
    assert "reaction_set_verified_at" in checklist
    assert "non-directory artifact path" in checklist
    assert "unreadable artifact paths" in checklist
    assert "unexpected extra files" in checklist
    assert "outside the artifact directory" in checklist
    assert "system` tag metadata" in checklist
    assert "ErrorResponse` schema" in checklist
    assert "--require-clean-source" in checklist


def test_release_check_validates_prepare_demo_data_output_artifact():
    repo = Path(__file__).resolve().parent.parent
    release_check = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")
    readme = (repo / "README.md").read_text(encoding="utf-8")
    checklist = (repo / "docs" / "release-checklist.md").read_text(encoding="utf-8")

    assert '"--summary-only"' in release_check
    assert '"--compact"' in release_check
    assert '"--output"' in release_check
    assert "stable_prepare_demo_summary(summary_payload) != stable_prepare_demo_summary(summary)" in release_check
    assert "stable_prepare_demo_summary(summary_output_payload) != stable_prepare_demo_summary(summary)" in release_check
    assert "validate_prepare_demo_summary_reviewer(summary, \"payload.summary\")" in release_check
    assert "validate_prepare_demo_summary_reviewer(summary_payload, \"--summary-only output\")" in release_check
    assert "validate_prepare_demo_summary_reviewer(summary_output_payload, \"--output summary\")" in release_check
    assert "python scripts/prepare_demo_data.py --summary-only --compact --output out/demo-summary.json" in readme
    assert "python scripts/prepare_demo_data.py --summary-only --compact --output out/demo-summary.json" in checklist


def test_export_openapi_script_writes_publishable_schema(tmp_path):
    export_openapi = load_export_openapi()
    output_path = tmp_path / "openapi.json"

    export_openapi.write_openapi(output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    tag_names = {tag["name"] for tag in payload["tags"]}
    assert payload["info"]["title"] == "paper-lab-agent"
    assert payload["info"]["version"] == "0.1.0"
    assert "/api/v1/health" in payload["paths"]
    assert "system" in tag_names
    assert payload["components"]["schemas"]["ErrorResponse"]


def test_export_openapi_script_runs_as_file(tmp_path):
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent
    output_path = tmp_path / "openapi.json"

    result = subprocess.run(
        [sys.executable, "scripts/export_openapi.py", "--output", str(output_path), "--compact"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["info"]["title"] == "paper-lab-agent"


def test_export_openapi_script_rejects_symlinked_output_file(tmp_path):
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent
    outside_path = tmp_path / "outside-openapi.json"
    outside_path.write_text("outside-original", encoding="utf-8")
    output_path = tmp_path / "out" / "openapi.json"
    output_path.parent.mkdir()
    output_path.symlink_to(outside_path)

    result = subprocess.run(
        [sys.executable, "scripts/export_openapi.py", "--output", str(output_path), "--compact"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert f"export_openapi failed: output path is not a regular file: {output_path}" in result.stderr
    assert outside_path.read_text(encoding="utf-8") == "outside-original"


def test_export_openapi_script_rejects_symlinked_output_parent(tmp_path):
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent
    outside_dir = tmp_path / "outside-out"
    outside_dir.mkdir()
    linked_parent = tmp_path / "out"
    linked_parent.symlink_to(outside_dir, target_is_directory=True)
    output_path = linked_parent / "openapi.json"

    result = subprocess.run(
        [sys.executable, "scripts/export_openapi.py", "--output", str(output_path), "--compact"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert f"export_openapi failed: output path parent is not a regular directory: {linked_parent}" in result.stderr
    assert not (outside_dir / "openapi.json").exists()


def test_export_release_artifacts_script_writes_handoff_bundle(tmp_path):
    import os
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent
    output_dir = tmp_path / "release"
    data_dir = tmp_path / "data"
    env = os.environ.copy()
    env["PAPER_LAB_DATA_DIR"] = str(data_dir)
    for key in [
        "DATABASE_PATH",
        "PAPER_LAB_PDF_DIR",
        "PAPER_LAB_TEI_DIR",
        "PAPER_LAB_TRANSLATION_DIR",
        "PAPER_LAB_EXPORT_DIR",
        "VECTOR_DB_PATH",
        "VECTOR_DB_BACKEND",
    ]:
        env.pop(key, None)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/export_release_artifacts.py",
            "--output-dir",
            str(output_dir),
            "--compact",
        ],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    stdout_manifest = json.loads(result.stdout)
    manifest = json.loads((output_dir / "release-manifest.json").read_text(encoding="utf-8"))
    demo_summary = json.loads((output_dir / "demo-summary.json").read_text(encoding="utf-8"))
    openapi = json.loads((output_dir / "openapi.json").read_text(encoding="utf-8"))

    assert stdout_manifest == manifest
    assert manifest["service"] == "paper-lab-agent"
    assert manifest["version"] == openapi["info"]["version"]
    assert manifest["artifacts"]["openapi"] == "openapi.json"
    assert manifest["artifacts"]["demo_summary"] == "demo-summary.json"
    expected_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    expected_branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    expected_dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    assert manifest["source"]["git_commit"] == expected_commit
    assert manifest["source"]["git_branch"] == expected_branch
    assert manifest["source"]["git_dirty"] is expected_dirty
    assert set(manifest["checksums"]) == {"openapi.json", "demo-summary.json", "release-manifest.json"}
    assert all(
        len(value) == 64 and all(character in string.hexdigits for character in value)
        for value in manifest["checksums"].values()
    )
    assert demo_summary["ready"] is True
    assert demo_summary["export_formats"] == ["json", "txt", "bolsig"]
    assert demo_summary["export_audit_entry_counts"] == {"json": 1, "txt": 1, "bolsig": 1}
    assert demo_summary["reaction_set_verified_by"] == "prepare-demo-data"
    assert demo_summary["reaction_set_verified_at"]
    assert manifest["demo_export_audit_entry_counts"] == demo_summary["export_audit_entry_counts"]
    assert manifest["demo_reaction_set_verified_by"] == demo_summary["reaction_set_verified_by"]
    assert manifest["demo_reaction_set_verified_at"] == demo_summary["reaction_set_verified_at"]
    assert "/api/v1/health" in openapi["paths"]


def test_export_release_artifacts_reports_openapi_write_failure(monkeypatch, tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    output_dir = tmp_path / "release"

    def fake_write_openapi(path, *, compact=False):
        return f"output path is not a regular file: {path}"

    monkeypatch.setattr(export_release_artifacts, "write_openapi", fake_write_openapi)

    report = export_release_artifacts.export_release_artifacts(output_dir, compact=True)

    assert report["ok"] is False
    assert report["output_dir"] == str(output_dir.resolve())
    assert report["issues"] == [
        f"OpenAPI artifact write failed: output path is not a regular file: {output_dir.resolve() / 'openapi.json'}"
    ]
    assert not (output_dir / "demo-summary.json").exists()
    assert not (output_dir / "release-manifest.json").exists()


def test_export_release_artifacts_reports_demo_summary_write_failure(monkeypatch, tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    output_dir = tmp_path / "release"
    original_write_json = export_release_artifacts.write_json

    def fake_write_json(path, payload, *, compact=False):
        if path.name == "demo-summary.json":
            raise OSError("disk full")
        original_write_json(path, payload, compact=compact)

    monkeypatch.setattr(export_release_artifacts, "write_json", fake_write_json)

    report = export_release_artifacts.export_release_artifacts(output_dir, compact=True)

    assert report["ok"] is False
    assert report["output_dir"] == str(output_dir.resolve())
    assert report["issues"] == ["Demo summary artifact write failed: disk full"]
    assert (output_dir / "openapi.json").exists()
    assert not (output_dir / "demo-summary.json").exists()
    assert not (output_dir / "release-manifest.json").exists()


def test_export_release_artifacts_reports_prepare_demo_failure(monkeypatch, tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    output_dir = tmp_path / "release"

    def fake_prepare_demo_data():
        raise RuntimeError("fixture setup failed")

    monkeypatch.setattr(export_release_artifacts, "prepare_demo_data", fake_prepare_demo_data)

    try:
        report = export_release_artifacts.export_release_artifacts(output_dir, compact=True)
    except RuntimeError as exc:
        raise AssertionError(
            "export_release_artifacts should report demo preparation failures instead of raising"
        ) from exc

    assert report["ok"] is False
    assert report["output_dir"] == str(output_dir.resolve())
    assert report["issues"] == ["Demo data preparation failed: fixture setup failed"]
    assert (output_dir / "openapi.json").exists()
    assert not (output_dir / "demo-summary.json").exists()
    assert not (output_dir / "release-manifest.json").exists()


def test_export_release_artifacts_removes_stale_outputs_on_prepare_demo_failure(monkeypatch, tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    output_dir = tmp_path / "release"
    output_dir.mkdir()
    stale_demo_summary = output_dir / "demo-summary.json"
    stale_manifest = output_dir / "release-manifest.json"
    stale_demo_summary.write_text('{"ready": true}\n', encoding="utf-8")
    stale_manifest.write_text('{"service": "paper-lab-agent"}\n', encoding="utf-8")

    def fake_prepare_demo_data():
        raise RuntimeError("fixture setup failed")

    monkeypatch.setattr(export_release_artifacts, "prepare_demo_data", fake_prepare_demo_data)

    report = export_release_artifacts.export_release_artifacts(output_dir, compact=True)

    assert report["ok"] is False
    assert report["issues"] == ["Demo data preparation failed: fixture setup failed"]
    assert (output_dir / "openapi.json").exists()
    assert not stale_demo_summary.exists()
    assert not stale_manifest.exists()


def test_export_release_artifacts_reports_stale_artifact_cleanup_failure(monkeypatch, tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    output_dir = tmp_path / "release"
    output_dir.mkdir()
    (output_dir / "openapi.json").write_text('{"stale": true}\n', encoding="utf-8")
    (output_dir / "demo-summary.json").write_text('{"ready": true}\n', encoding="utf-8")
    (output_dir / "release-manifest.json").write_text('{"service": "paper-lab-agent"}\n', encoding="utf-8")
    original_unlink = export_release_artifacts.Path.unlink

    def fake_unlink(path, *, missing_ok=False):
        if path.name == "demo-summary.json":
            raise OSError("permission denied")
        return original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(export_release_artifacts.Path, "unlink", fake_unlink)

    try:
        report = export_release_artifacts.export_release_artifacts(output_dir, compact=True)
    except OSError as exc:
        raise AssertionError(
            "export_release_artifacts should report stale artifact cleanup failures instead of raising"
        ) from exc

    assert report["ok"] is False
    assert report["output_dir"] == str(output_dir.resolve())
    assert report["issues"] == ["release artifact cleanup failed: permission denied"]


def test_export_release_artifacts_reports_manifest_write_failure(monkeypatch, tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    output_dir = tmp_path / "release"
    original_write_json = export_release_artifacts.write_json

    def fake_write_json(path, payload, *, compact=False):
        if path.name == "release-manifest.json":
            raise OSError("permission denied")
        original_write_json(path, payload, compact=compact)

    monkeypatch.setattr(export_release_artifacts, "write_json", fake_write_json)

    report = export_release_artifacts.export_release_artifacts(output_dir, compact=True)

    assert report["ok"] is False
    assert report["output_dir"] == str(output_dir.resolve())
    assert report["issues"] == ["Release manifest artifact write failed: permission denied"]
    assert (output_dir / "openapi.json").exists()
    assert (output_dir / "demo-summary.json").exists()
    assert not (output_dir / "release-manifest.json").exists()


def test_export_release_artifacts_reports_output_dir_not_directory(tmp_path):
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent
    output_dir = tmp_path / "release"
    output_dir.write_text("not a directory", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/export_release_artifacts.py",
            "--output-dir",
            str(output_dir),
            "--compact",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert f"release artifact output directory is not a directory: {output_dir.resolve()}" in payload["issues"]
    assert "Traceback" not in result.stderr


def test_export_release_artifacts_rejects_output_dir_symlink(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    output_dir = tmp_path / "release"
    outside_dir = tmp_path / "outside-release"
    outside_dir.mkdir()
    output_dir.symlink_to(outside_dir, target_is_directory=True)

    report = export_release_artifacts.export_release_artifacts(output_dir, compact=True)

    assert report["ok"] is False
    assert f"release artifact output directory is not a regular directory: {output_dir}" in report["issues"]
    assert output_dir.is_symlink()
    assert not (outside_dir / "openapi.json").exists()
    assert not (outside_dir / "demo-summary.json").exists()


def test_export_release_artifacts_rejects_output_dir_symlink_parent(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    outside_dir = tmp_path / "outside-release-parent"
    linked_parent = tmp_path / "linked-parent"
    output_dir = linked_parent / "release"
    outside_dir.mkdir()
    linked_parent.symlink_to(outside_dir, target_is_directory=True)

    report = export_release_artifacts.export_release_artifacts(output_dir, compact=True)

    assert report["ok"] is False
    assert f"release artifact output directory parent is not a regular directory: {linked_parent}" in report["issues"]
    assert linked_parent.is_symlink()
    assert not (outside_dir / "release" / "openapi.json").exists()
    assert not (outside_dir / "release" / "demo-summary.json").exists()


def test_export_release_artifacts_rejects_output_dir_symlink_ancestor(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    outside_dir = tmp_path / "outside-release-root"
    linked_root = tmp_path / "linked-root"
    output_dir = linked_root / "nested" / "release"
    outside_dir.mkdir()
    linked_root.symlink_to(outside_dir, target_is_directory=True)

    report = export_release_artifacts.export_release_artifacts(output_dir, compact=True)

    assert report["ok"] is False
    assert f"release artifact output directory parent is not a regular directory: {linked_root}" in report["issues"]
    assert linked_root.is_symlink()
    assert not (outside_dir / "nested" / "release" / "openapi.json").exists()
    assert not (outside_dir / "nested" / "release" / "demo-summary.json").exists()


def test_export_release_artifacts_rejects_dirty_output_dir(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    output_dir = tmp_path / "release"
    output_dir.mkdir()
    stale_path = output_dir / "old-demo-summary.json"
    stale_path.write_text("stale", encoding="utf-8")

    report = export_release_artifacts.export_release_artifacts(output_dir, compact=True)

    assert report["ok"] is False
    assert f"release artifact output directory contains unexpected files: ['old-demo-summary.json']" in report["issues"]
    assert stale_path.read_text(encoding="utf-8") == "stale"
    assert not (output_dir / "openapi.json").exists()


def test_export_release_artifacts_reports_expected_artifact_path_not_file(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    output_dir = tmp_path / "release"
    openapi_path = output_dir / "openapi.json"
    output_dir.mkdir()
    openapi_path.mkdir()

    report = export_release_artifacts.export_release_artifacts(output_dir, compact=True)

    assert report["ok"] is False
    assert f"release artifact output path is not a file: {openapi_path.resolve()}" in report["issues"]
    assert openapi_path.is_dir()
    assert not (output_dir / "demo-summary.json").exists()


def test_export_release_artifacts_rejects_expected_artifact_symlink(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    output_dir = tmp_path / "release"
    outside_path = tmp_path / "outside-openapi.json"
    openapi_path = output_dir / "openapi.json"
    output_dir.mkdir()
    outside_path.write_text("do not overwrite", encoding="utf-8")
    openapi_path.symlink_to(outside_path)

    report = export_release_artifacts.export_release_artifacts(output_dir, compact=True)

    assert report["ok"] is False
    assert f"release artifact output path is not a regular file: {output_dir.resolve() / 'openapi.json'}" in report["issues"]
    assert outside_path.read_text(encoding="utf-8") == "do not overwrite"
    assert not (output_dir / "demo-summary.json").exists()


def test_validate_release_artifacts_script_accepts_handoff_bundle(tmp_path):
    import os
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent
    output_dir = tmp_path / "release"
    data_dir = tmp_path / "data"
    env = os.environ.copy()
    env["PAPER_LAB_DATA_DIR"] = str(data_dir)
    for key in [
        "DATABASE_PATH",
        "PAPER_LAB_PDF_DIR",
        "PAPER_LAB_TEI_DIR",
        "PAPER_LAB_TRANSLATION_DIR",
        "PAPER_LAB_EXPORT_DIR",
        "VECTOR_DB_PATH",
        "VECTOR_DB_BACKEND",
    ]:
        env.pop(key, None)

    export_result = subprocess.run(
        [
            sys.executable,
            "scripts/export_release_artifacts.py",
            "--output-dir",
            str(output_dir),
            "--compact",
        ],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert export_result.returncode == 0, export_result.stderr

    validate_result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_release_artifacts.py",
            "--artifact-dir",
            str(output_dir),
            "--compact",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert validate_result.returncode == 0, validate_result.stderr
    payload = json.loads(validate_result.stdout)
    assert payload["ok"] is True
    assert payload["artifact_dir"] == str(output_dir)
    assert payload["service"] == "paper-lab-agent"
    assert payload["version"] == "0.1.0"
    assert payload["source"]["git_commit"]
    assert payload["source"]["git_branch"] == subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert isinstance(payload["source"]["git_dirty"], bool)
    assert payload["demo_ready"] is True
    assert payload["demo_export_formats"] == ["json", "txt", "bolsig"]
    assert payload["demo_export_audit_entry_counts"] == {"json": 1, "txt": 1, "bolsig": 1}
    assert payload["demo_reaction_set_verified_by"] == "prepare-demo-data"
    assert payload["demo_reaction_set_verified_at"]
    assert payload["openapi_path_count"] == 28


def test_validate_release_artifacts_rejects_artifact_dir_symlink(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    validate_release_artifacts = load_validate_release_artifacts()
    artifact_dir = tmp_path / "release"
    outside_dir = tmp_path / "outside-release"
    outside_dir.mkdir()
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-26T13:30:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-26T13:30:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = outside_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (outside_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(outside_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (outside_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    artifact_dir.symlink_to(outside_dir, target_is_directory=True)

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert report["ok"] is False
    assert f"release artifact directory is not a regular directory: {artifact_dir}" in report["issues"]
    assert artifact_dir.is_symlink()
    assert (outside_dir / "release-manifest.json").exists()


def test_validate_release_artifacts_rejects_artifact_dir_symlink_parent(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    validate_release_artifacts = load_validate_release_artifacts()
    outside_dir = tmp_path / "outside-release-parent"
    linked_parent = tmp_path / "linked-parent"
    artifact_dir = linked_parent / "release"
    outside_artifact_dir = outside_dir / "release"
    outside_artifact_dir.mkdir(parents=True)
    linked_parent.symlink_to(outside_dir, target_is_directory=True)
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-26T14:10:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-26T14:10:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = outside_artifact_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (outside_artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(
        outside_artifact_dir / "demo-summary.json"
    )
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (outside_artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert report["ok"] is False
    assert f"release artifact directory parent is not a regular directory: {linked_parent}" in report["issues"]
    assert linked_parent.is_symlink()
    assert (outside_artifact_dir / "release-manifest.json").exists()


def test_validate_release_artifacts_rejects_artifact_dir_symlink_ancestor(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    validate_release_artifacts = load_validate_release_artifacts()
    outside_dir = tmp_path / "outside-release-root"
    linked_root = tmp_path / "linked-root"
    artifact_dir = linked_root / "nested" / "release"
    outside_artifact_dir = outside_dir / "nested" / "release"
    outside_artifact_dir.mkdir(parents=True)
    linked_root.symlink_to(outside_dir, target_is_directory=True)
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-27T12:10:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-27T12:10:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = outside_artifact_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (outside_artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(
        outside_artifact_dir / "demo-summary.json"
    )
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (outside_artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert report["ok"] is False
    assert f"release artifact directory parent is not a regular directory: {linked_root}" in report["issues"]
    assert linked_root.is_symlink()
    assert (outside_artifact_dir / "release-manifest.json").exists()


def test_validate_release_artifacts_rejects_required_artifact_symlink(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    validate_release_artifacts = load_validate_release_artifacts()
    artifact_dir = tmp_path / "release"
    outside_path = tmp_path / "outside-openapi.json"
    artifact_dir.mkdir()
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-26T13:40:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-26T13:40:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    outside_path.write_text(json.dumps(openapi), encoding="utf-8")
    openapi_path = artifact_dir / "openapi.json"
    openapi_path.symlink_to(outside_path)
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(outside_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert report["ok"] is False
    assert f"OpenAPI artifact is not a regular file: {openapi_path}" in report["issues"]
    assert openapi_path.is_symlink()
    assert outside_path.exists()


def test_validate_release_artifacts_reports_manifest_audit_count_mismatch(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    validate_release_artifacts = load_validate_release_artifacts()
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 0, "txt": 1, "bolsig": 1},
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    (artifact_dir / "openapi.json").write_text(json.dumps(openapi), encoding="utf-8")
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(artifact_dir / "openapi.json")
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert "release manifest demo_export_audit_entry_counts mismatch: {'json': 0, 'txt': 1, 'bolsig': 1}" in report["issues"]


def test_validate_release_artifacts_requires_demo_audit_summary(tmp_path):
    validate_release_artifacts = load_validate_release_artifacts()
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    (artifact_dir / "openapi.json").write_text(
        json.dumps(
            {
                "info": {"title": "paper-lab-agent", "version": "0.1.0"},
                "paths": {"/api/v1/health": {}},
            }
        ),
        encoding="utf-8",
    )
    (artifact_dir / "demo-summary.json").write_text(
        json.dumps({"ready": True, "export_formats": ["json", "txt", "bolsig"]}),
        encoding="utf-8",
    )
    (artifact_dir / "release-manifest.json").write_text("{}", encoding="utf-8")

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert "demo summary export_audit_entry_counts must include positive counts for: json, txt, bolsig" in report["issues"]


def test_validate_release_artifacts_requires_demo_reviewer_timestamp(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    validate_release_artifacts = load_validate_release_artifacts()
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "not-a-timestamp",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "not-a-timestamp",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    (artifact_dir / "openapi.json").write_text(json.dumps(openapi), encoding="utf-8")
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(artifact_dir / "openapi.json")
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert "demo summary reaction_set_verified_at must be an ISO8601 timestamp" in report["issues"]


def test_validate_release_artifacts_requires_handoff_openapi_metadata(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    validate_release_artifacts = load_validate_release_artifacts()
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "papers", "description": "Paper search"}],
        "components": {"schemas": {}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-26T11:55:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-26T11:55:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    (artifact_dir / "openapi.json").write_text(json.dumps(openapi), encoding="utf-8")
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(artifact_dir / "openapi.json")
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert "OpenAPI missing system tag metadata" in report["issues"]
    assert "OpenAPI missing ErrorResponse schema" in report["issues"]


def test_validate_release_artifacts_rejects_unexpected_handoff_files(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    validate_release_artifacts = load_validate_release_artifacts()
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-26T12:00:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-26T12:00:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    (artifact_dir / "openapi.json").write_text(json.dumps(openapi), encoding="utf-8")
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(artifact_dir / "openapi.json")
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (artifact_dir / "old-demo-summary.json").write_text("{}", encoding="utf-8")

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert "release artifact directory contains unexpected files: ['old-demo-summary.json']" in report["issues"]


def test_validate_release_artifacts_reports_unreadable_required_artifact(tmp_path):
    validate_release_artifacts = load_validate_release_artifacts()
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    (artifact_dir / "openapi.json").mkdir()
    (artifact_dir / "demo-summary.json").write_text("{}", encoding="utf-8")
    (artifact_dir / "release-manifest.json").write_text("{}", encoding="utf-8")

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert any(issue.startswith("OpenAPI artifact unreadable:") for issue in report["issues"])


def test_validate_release_artifacts_reports_checksum_artifact_not_file(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    validate_release_artifacts = load_validate_release_artifacts()
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    openapi_path = artifact_dir / "openapi.json"
    openapi_path.mkdir()
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-26T12:45:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-26T12:45:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "0" * 64,
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert report["ok"] is False
    assert any(issue.startswith("OpenAPI artifact unreadable:") for issue in report["issues"])
    assert f"checksum unavailable: openapi.json is not a file: {openapi_path.resolve()}" in report["issues"]


def test_validate_release_artifacts_reports_non_utf8_required_artifact(tmp_path):
    validate_release_artifacts = load_validate_release_artifacts()
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    (artifact_dir / "openapi.json").write_bytes(b"\xff\xfe\x00")
    (artifact_dir / "demo-summary.json").write_text("{}", encoding="utf-8")
    (artifact_dir / "release-manifest.json").write_text("{}", encoding="utf-8")

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert any(issue.startswith("OpenAPI artifact unreadable:") for issue in report["issues"])


def test_validate_release_artifacts_reports_artifact_dir_not_directory(tmp_path):
    validate_release_artifacts = load_validate_release_artifacts()
    artifact_dir = tmp_path / "release"
    artifact_dir.write_text("not a directory", encoding="utf-8")

    report = validate_release_artifacts.validate_release_artifacts(artifact_dir)

    assert f"release artifact directory is not a directory: {artifact_dir.resolve()}" in report["issues"]


def test_validate_release_artifacts_script_rejects_tampered_artifact(tmp_path):
    import os
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent
    output_dir = tmp_path / "release"
    data_dir = tmp_path / "data"
    env = os.environ.copy()
    env["PAPER_LAB_DATA_DIR"] = str(data_dir)
    for key in [
        "DATABASE_PATH",
        "PAPER_LAB_PDF_DIR",
        "PAPER_LAB_TEI_DIR",
        "PAPER_LAB_TRANSLATION_DIR",
        "PAPER_LAB_EXPORT_DIR",
        "VECTOR_DB_PATH",
        "VECTOR_DB_BACKEND",
    ]:
        env.pop(key, None)

    export_result = subprocess.run(
        [
            sys.executable,
            "scripts/export_release_artifacts.py",
            "--output-dir",
            str(output_dir),
            "--compact",
        ],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert export_result.returncode == 0, export_result.stderr

    demo_summary_path = output_dir / "demo-summary.json"
    demo_summary = json.loads(demo_summary_path.read_text(encoding="utf-8"))
    demo_summary["ready"] = False
    demo_summary_path.write_text(json.dumps(demo_summary, ensure_ascii=False), encoding="utf-8")

    validate_result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_release_artifacts.py",
            "--artifact-dir",
            str(output_dir),
            "--compact",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert validate_result.returncode == 1
    payload = json.loads(validate_result.stdout)
    assert payload["ok"] is False
    assert any("checksum mismatch: demo-summary.json" in issue for issue in payload["issues"])


def test_validate_release_artifacts_script_can_require_clean_source(tmp_path):
    import os
    import subprocess
    import sys

    export_release_artifacts = load_export_release_artifacts()
    repo = Path(__file__).resolve().parent.parent
    output_dir = tmp_path / "release"
    data_dir = tmp_path / "data"
    env = os.environ.copy()
    env["PAPER_LAB_DATA_DIR"] = str(data_dir)
    for key in [
        "DATABASE_PATH",
        "PAPER_LAB_PDF_DIR",
        "PAPER_LAB_TEI_DIR",
        "PAPER_LAB_TRANSLATION_DIR",
        "PAPER_LAB_EXPORT_DIR",
        "VECTOR_DB_PATH",
        "VECTOR_DB_BACKEND",
    ]:
        env.pop(key, None)

    export_result = subprocess.run(
        [
            sys.executable,
            "scripts/export_release_artifacts.py",
            "--output-dir",
            str(output_dir),
            "--compact",
        ],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert export_result.returncode == 0, export_result.stderr

    manifest_path = output_dir / "release-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source"]["git_dirty"] = True
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    validate_result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_release_artifacts.py",
            "--artifact-dir",
            str(output_dir),
            "--require-clean-source",
            "--compact",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert validate_result.returncode == 1
    payload = json.loads(validate_result.stdout)
    assert payload["ok"] is False
    assert "release manifest source.git_dirty must be false for clean-source validation" in payload["issues"]


def test_package_release_artifacts_script_writes_zip_bundle(tmp_path):
    import os
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent
    output_dir = tmp_path / "release"
    package_path = tmp_path / "paper-lab-agent-release.zip"
    data_dir = tmp_path / "data"
    env = os.environ.copy()
    env["PAPER_LAB_DATA_DIR"] = str(data_dir)
    for key in [
        "DATABASE_PATH",
        "PAPER_LAB_PDF_DIR",
        "PAPER_LAB_TEI_DIR",
        "PAPER_LAB_TRANSLATION_DIR",
        "PAPER_LAB_EXPORT_DIR",
        "VECTOR_DB_PATH",
        "VECTOR_DB_BACKEND",
    ]:
        env.pop(key, None)

    export_result = subprocess.run(
        [
            sys.executable,
            "scripts/export_release_artifacts.py",
            "--output-dir",
            str(output_dir),
            "--compact",
        ],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert export_result.returncode == 0, export_result.stderr

    package_result = subprocess.run(
        [
            sys.executable,
            "scripts/package_release_artifacts.py",
            "--artifact-dir",
            str(output_dir),
            "--output",
            str(package_path),
            "--compact",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert package_result.returncode == 0, package_result.stderr
    payload = json.loads(package_result.stdout)
    assert payload["ok"] is True
    assert payload["package_path"] == str(package_path)
    assert payload["artifact_count"] == 3
    assert payload["artifact_names"] == [
        "demo-summary.json",
        "openapi.json",
        "release-manifest.json",
    ]
    assert len(payload["package_sha256"]) == 64
    assert payload["source"]["git_commit"]
    assert payload["demo_ready"] is True
    assert payload["demo_export_formats"] == ["json", "txt", "bolsig"]
    assert payload["demo_export_audit_entry_counts"] == {"json": 1, "txt": 1, "bolsig": 1}
    assert payload["demo_reaction_set_verified_by"] == "prepare-demo-data"
    assert payload["demo_reaction_set_verified_at"]
    assert package_path.exists()
    with zipfile.ZipFile(package_path) as archive:
        assert sorted(archive.namelist()) == [
            "demo-summary.json",
            "openapi.json",
            "release-manifest.json",
        ]

    validate_package_result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_release_package.py",
            "--package",
            str(package_path),
            "--compact",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert validate_package_result.returncode == 0, validate_package_result.stderr
    validate_payload = json.loads(validate_package_result.stdout)
    assert validate_payload["ok"] is True
    assert validate_payload["package_path"] == str(package_path)
    assert validate_payload["artifact_count"] == 3
    assert validate_payload["artifact_names"] == [
        "demo-summary.json",
        "openapi.json",
        "release-manifest.json",
    ]
    assert validate_payload["source"]["git_commit"]
    assert validate_payload["demo_ready"] is True
    assert validate_payload["demo_export_formats"] == ["json", "txt", "bolsig"]
    assert validate_payload["demo_export_audit_entry_counts"] == {"json": 1, "txt": 1, "bolsig": 1}
    assert validate_payload["demo_reaction_set_verified_by"] == "prepare-demo-data"
    assert validate_payload["demo_reaction_set_verified_at"]


def test_package_release_artifacts_removes_stale_output_on_validation_failure(tmp_path):
    package_release_artifacts = load_package_release_artifacts()
    artifact_dir = tmp_path / "invalid-release"
    output_path = tmp_path / "paper-lab-agent-release.zip"
    artifact_dir.mkdir()
    output_path.write_bytes(b"stale release package")

    report = package_release_artifacts.package_release_artifacts(artifact_dir, output_path)

    assert report["ok"] is False
    assert not output_path.exists()
    assert any("missing" in issue for issue in report["issues"])


def test_package_release_artifacts_reports_validator_runtime_failure(monkeypatch, tmp_path):
    package_release_artifacts = load_package_release_artifacts()
    artifact_dir = tmp_path / "release"
    output_path = tmp_path / "paper-lab-agent-release.zip"
    artifact_dir.mkdir()
    output_path.write_bytes(b"stale release package")

    def fake_validate_release_artifacts(path, *, require_clean_source=False):
        raise RuntimeError("manifest parser crashed")

    monkeypatch.setattr(
        package_release_artifacts,
        "validate_release_artifacts",
        fake_validate_release_artifacts,
    )

    try:
        report = package_release_artifacts.package_release_artifacts(artifact_dir, output_path)
    except RuntimeError as exc:
        raise AssertionError(
            "package_release_artifacts should report validator failures instead of raising"
        ) from exc

    assert report["ok"] is False
    assert report["artifact_dir"] == str(artifact_dir.resolve())
    assert report["package_path"] == str(output_path.resolve())
    assert report["package_sha256"] is None
    assert report["artifact_count"] == 0
    assert report["artifact_names"] == []
    assert report["issues"] == ["release artifact validation failed: manifest parser crashed"]
    assert not output_path.exists()


def test_package_release_artifacts_reports_stale_output_cleanup_failure(monkeypatch, tmp_path):
    package_release_artifacts = load_package_release_artifacts()
    artifact_dir = tmp_path / "invalid-release"
    output_path = tmp_path / "paper-lab-agent-release.zip"
    artifact_dir.mkdir()
    output_path.write_bytes(b"stale release package")
    original_unlink = package_release_artifacts.Path.unlink

    def fake_unlink(path, *, missing_ok=False):
        if path == output_path:
            raise OSError("permission denied")
        return original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(package_release_artifacts.Path, "unlink", fake_unlink)

    try:
        report = package_release_artifacts.package_release_artifacts(artifact_dir, output_path)
    except OSError as exc:
        raise AssertionError(
            "package_release_artifacts should report stale package cleanup failures instead of raising"
        ) from exc

    assert report["ok"] is False
    assert report["artifact_dir"] == str(artifact_dir.resolve())
    assert report["package_path"] == str(output_path.resolve())
    assert report["package_sha256"] is None
    assert report["artifact_count"] == 0
    assert report["artifact_names"] == []
    assert report["issues"] == ["release package cleanup failed: permission denied"]
    assert output_path.exists()


def test_package_release_artifacts_reports_zip_write_failure(monkeypatch, tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    package_release_artifacts = load_package_release_artifacts()
    artifact_dir = tmp_path / "release"
    output_path = tmp_path / "paper-lab-agent-release.zip"
    export_release_artifacts.export_release_artifacts(artifact_dir, compact=True)

    class FailingZipFile:
        def __init__(self, *args, **kwargs):
            raise OSError("disk full")

    monkeypatch.setattr(package_release_artifacts.zipfile, "ZipFile", FailingZipFile)

    report = package_release_artifacts.package_release_artifacts(artifact_dir, output_path)

    assert report["ok"] is False
    assert report["artifact_dir"] == str(artifact_dir.resolve())
    assert report["package_path"] == str(output_path.resolve())
    assert report["package_sha256"] is None
    assert report["artifact_count"] == 0
    assert report["artifact_names"] == []
    assert report["issues"] == ["release package write failed: disk full"]
    assert not output_path.exists()


def test_package_release_artifacts_rejects_artifact_dir_symlink(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    package_release_artifacts = load_package_release_artifacts()
    artifact_dir = tmp_path / "release"
    outside_dir = tmp_path / "outside-release"
    output_path = tmp_path / "paper-lab-agent-release.zip"
    outside_dir.mkdir()
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-26T14:00:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-26T14:00:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = outside_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (outside_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(outside_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (outside_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    artifact_dir.symlink_to(outside_dir, target_is_directory=True)

    report = package_release_artifacts.package_release_artifacts(artifact_dir, output_path)

    assert report["ok"] is False
    assert f"release artifact directory is not a regular directory: {artifact_dir.absolute()}" in report["issues"]
    assert artifact_dir.is_symlink()
    assert not output_path.exists()


def test_package_release_artifacts_rejects_artifact_dir_symlink_ancestor(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    package_release_artifacts = load_package_release_artifacts()
    outside_dir = tmp_path / "outside-release-root"
    linked_root = tmp_path / "linked-root"
    artifact_dir = linked_root / "nested" / "release"
    outside_artifact_dir = outside_dir / "nested" / "release"
    output_path = tmp_path / "paper-lab-agent-release.zip"
    outside_artifact_dir.mkdir(parents=True)
    linked_root.symlink_to(outside_dir, target_is_directory=True)
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-27T12:40:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-27T12:40:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = outside_artifact_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (outside_artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(
        outside_artifact_dir / "demo-summary.json"
    )
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (outside_artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = package_release_artifacts.package_release_artifacts(artifact_dir, output_path)

    assert report["ok"] is False
    assert f"release artifact directory parent is not a regular directory: {linked_root}" in report["issues"]
    assert linked_root.is_symlink()
    assert not output_path.exists()


def test_package_release_artifacts_reports_output_path_not_file(tmp_path):
    package_release_artifacts = load_package_release_artifacts()
    artifact_dir = tmp_path / "invalid-release"
    output_path = tmp_path / "paper-lab-agent-release.zip"
    artifact_dir.mkdir()
    output_path.mkdir()

    report = package_release_artifacts.package_release_artifacts(artifact_dir, output_path)

    assert report["ok"] is False
    assert f"release package output is not a file: {output_path.resolve()}" in report["issues"]
    assert output_path.is_dir()


def test_package_release_artifacts_rejects_output_symlink(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    package_release_artifacts = load_package_release_artifacts()
    artifact_dir = tmp_path / "release"
    output_path = tmp_path / "paper-lab-agent-release.zip"
    outside_path = tmp_path / "outside-package.zip"
    artifact_dir.mkdir()
    outside_path.write_bytes(b"do not overwrite")
    output_path.symlink_to(outside_path)
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-26T13:10:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-26T13:10:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = artifact_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = package_release_artifacts.package_release_artifacts(artifact_dir, output_path)

    assert report["ok"] is False
    assert f"release package output is not a regular file: {output_path}" in report["issues"]
    assert outside_path.read_bytes() == b"do not overwrite"
    assert output_path.is_symlink()


def test_package_release_artifacts_rejects_output_parent_symlink(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    package_release_artifacts = load_package_release_artifacts()
    artifact_dir = tmp_path / "release"
    outside_dir = tmp_path / "outside-package-parent"
    linked_parent = tmp_path / "linked-parent"
    output_path = linked_parent / "paper-lab-agent-release.zip"
    artifact_dir.mkdir()
    outside_dir.mkdir()
    linked_parent.symlink_to(outside_dir, target_is_directory=True)
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-26T13:50:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-26T13:50:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = artifact_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = package_release_artifacts.package_release_artifacts(artifact_dir, output_path)

    assert report["ok"] is False
    assert f"release package output parent is not a regular directory: {linked_parent}" in report["issues"]
    assert linked_parent.is_symlink()
    assert not (outside_dir / "paper-lab-agent-release.zip").exists()


def test_package_release_artifacts_rejects_output_ancestor_symlink(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    package_release_artifacts = load_package_release_artifacts()
    artifact_dir = tmp_path / "release"
    outside_dir = tmp_path / "outside-package-root"
    linked_root = tmp_path / "linked-root"
    output_path = linked_root / "nested" / "paper-lab-agent-release.zip"
    artifact_dir.mkdir()
    outside_dir.mkdir()
    linked_root.symlink_to(outside_dir, target_is_directory=True)
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-27T13:45:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-27T13:45:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = artifact_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = package_release_artifacts.package_release_artifacts(artifact_dir, output_path)

    assert report["ok"] is False
    assert f"release package output parent is not a regular directory: {linked_root}" in report["issues"]
    assert linked_root.is_symlink()
    assert not (outside_dir / "nested" / "paper-lab-agent-release.zip").exists()


def test_package_release_artifacts_reports_output_parent_not_directory(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    package_release_artifacts = load_package_release_artifacts()
    artifact_dir = tmp_path / "release"
    output_parent = tmp_path / "packages"
    output_path = output_parent / "paper-lab-agent-release.zip"
    artifact_dir.mkdir()
    output_parent.write_text("not a directory", encoding="utf-8")
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-26T12:50:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-26T12:50:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = artifact_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    report = package_release_artifacts.package_release_artifacts(artifact_dir, output_path)

    assert report["ok"] is False
    assert f"release package output parent is not a directory: {output_parent.resolve()}" in report["issues"]
    assert output_parent.is_file()


def test_package_release_artifacts_rejects_output_inside_artifact_dir(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    package_release_artifacts = load_package_release_artifacts()
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-26T12:05:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-26T12:05:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = artifact_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    original_openapi = openapi_path.read_bytes()

    report = package_release_artifacts.package_release_artifacts(artifact_dir, openapi_path)

    assert report["ok"] is False
    assert "release package output must not be inside the artifact directory" in report["issues"]
    assert openapi_path.read_bytes() == original_openapi


def test_validate_release_package_script_rejects_tampered_zip_artifact(tmp_path):
    import os
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent
    output_dir = tmp_path / "release"
    package_path = tmp_path / "paper-lab-agent-release.zip"
    data_dir = tmp_path / "data"
    env = os.environ.copy()
    env["PAPER_LAB_DATA_DIR"] = str(data_dir)
    for key in [
        "DATABASE_PATH",
        "PAPER_LAB_PDF_DIR",
        "PAPER_LAB_TEI_DIR",
        "PAPER_LAB_TRANSLATION_DIR",
        "PAPER_LAB_EXPORT_DIR",
        "VECTOR_DB_PATH",
        "VECTOR_DB_BACKEND",
    ]:
        env.pop(key, None)

    export_result = subprocess.run(
        [
            sys.executable,
            "scripts/export_release_artifacts.py",
            "--output-dir",
            str(output_dir),
            "--compact",
        ],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert export_result.returncode == 0, export_result.stderr

    with zipfile.ZipFile(package_path, mode="w") as archive:
        for artifact_path in sorted(output_dir.iterdir()):
            payload = artifact_path.read_bytes()
            if artifact_path.name == "demo-summary.json":
                demo_summary = json.loads(payload.decode("utf-8"))
                demo_summary["ready"] = False
                payload = json.dumps(demo_summary, ensure_ascii=False).encode("utf-8")
            archive.writestr(artifact_path.name, payload)

    validate_package_result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_release_package.py",
            "--package",
            str(package_path),
            "--compact",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert validate_package_result.returncode == 1
    payload = json.loads(validate_package_result.stdout)
    assert payload["ok"] is False
    assert any("checksum mismatch: demo-summary.json" in issue for issue in payload["issues"])


def test_validate_release_package_reports_package_path_not_file(tmp_path):
    validate_release_package = load_validate_release_package()
    package_path = tmp_path / "paper-lab-agent-release.zip"
    package_path.mkdir()

    report = validate_release_package.validate_release_package(package_path)

    assert report["ok"] is False
    assert f"release package is not a file: {package_path.resolve()}" in report["issues"]


def test_validate_release_package_reports_zip_read_failure(monkeypatch, tmp_path):
    validate_release_package = load_validate_release_package()
    package_path = tmp_path / "paper-lab-agent-release.zip"
    package_path.write_bytes(b"zip bytes")

    class FailingZipFile:
        def __init__(self, *args, **kwargs):
            raise OSError("input/output error")

    monkeypatch.setattr(validate_release_package.zipfile, "ZipFile", FailingZipFile)

    report = validate_release_package.validate_release_package(package_path)

    assert report["ok"] is False
    assert report["package_path"] == str(package_path.resolve())
    assert len(report["package_sha256"]) == 64
    assert report["artifact_count"] == 0
    assert report["artifact_names"] == []
    assert report["issues"] == ["release package unreadable: input/output error"]


def test_validate_release_package_rejects_package_symlink(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    validate_release_package = load_validate_release_package()
    artifact_dir = tmp_path / "release"
    package_path = tmp_path / "paper-lab-agent-release.zip"
    outside_path = tmp_path / "outside-package.zip"
    artifact_dir.mkdir()
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-26T13:20:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-26T13:20:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = artifact_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with zipfile.ZipFile(outside_path, mode="w") as archive:
        for artifact_path in sorted(artifact_dir.iterdir()):
            archive.write(artifact_path, arcname=artifact_path.name)
    package_path.symlink_to(outside_path)

    report = validate_release_package.validate_release_package(package_path)

    assert report["ok"] is False
    assert f"release package is not a regular file: {package_path}" in report["issues"]
    assert package_path.is_symlink()
    assert outside_path.exists()


def test_validate_release_package_rejects_package_parent_symlink(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    validate_release_package = load_validate_release_package()
    artifact_dir = tmp_path / "release"
    outside_dir = tmp_path / "outside-package-parent"
    linked_parent = tmp_path / "linked-parent"
    package_path = linked_parent / "paper-lab-agent-release.zip"
    outside_package_path = outside_dir / "paper-lab-agent-release.zip"
    artifact_dir.mkdir()
    outside_dir.mkdir()
    linked_parent.symlink_to(outside_dir, target_is_directory=True)
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-27T11:30:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-27T11:30:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = artifact_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with zipfile.ZipFile(outside_package_path, mode="w") as archive:
        for artifact_path in sorted(artifact_dir.iterdir()):
            archive.write(artifact_path, arcname=artifact_path.name)

    report = validate_release_package.validate_release_package(package_path)

    assert report["ok"] is False
    assert f"release package parent is not a regular directory: {linked_parent}" in report["issues"]
    assert linked_parent.is_symlink()
    assert outside_package_path.exists()


def test_validate_release_package_rejects_package_ancestor_symlink(tmp_path):
    export_release_artifacts = load_export_release_artifacts()
    validate_release_package = load_validate_release_package()
    artifact_dir = tmp_path / "release"
    outside_dir = tmp_path / "outside-package-root"
    linked_root = tmp_path / "linked-root"
    package_path = linked_root / "nested" / "paper-lab-agent-release.zip"
    outside_package_path = outside_dir / "nested" / "paper-lab-agent-release.zip"
    artifact_dir.mkdir()
    outside_package_path.parent.mkdir(parents=True)
    linked_root.symlink_to(outside_dir, target_is_directory=True)
    openapi = {
        "info": {"title": "paper-lab-agent", "version": "0.1.0"},
        "paths": {"/api/v1/health": {}},
        "tags": [{"name": "system", "description": "System status"}],
        "components": {"schemas": {"ErrorResponse": {"type": "object"}}},
    }
    demo_summary = {
        "ready": True,
        "export_formats": ["json", "txt", "bolsig"],
        "export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "reaction_set_verified_by": "prepare-demo-data",
        "reaction_set_verified_at": "2026-06-27T13:20:00",
    }
    manifest = {
        "service": "paper-lab-agent",
        "version": "0.1.0",
        "artifacts": {
            "openapi": "openapi.json",
            "demo_summary": "demo-summary.json",
            "manifest": "release-manifest.json",
        },
        "demo_ready": True,
        "demo_export_formats": ["json", "txt", "bolsig"],
        "demo_export_audit_entry_counts": {"json": 1, "txt": 1, "bolsig": 1},
        "demo_reaction_set_verified_by": "prepare-demo-data",
        "demo_reaction_set_verified_at": "2026-06-27T13:20:00",
        "openapi_path_count": 1,
        "source": {
            "git_commit": "a" * 40,
            "git_branch": "phase/5-experiment-lab-artifacts",
            "git_dirty": False,
        },
        "checksums": {
            "openapi.json": "",
            "demo-summary.json": "",
            "release-manifest.json": "",
        },
    }
    openapi_path = artifact_dir / "openapi.json"
    openapi_path.write_text(json.dumps(openapi), encoding="utf-8")
    (artifact_dir / "demo-summary.json").write_text(json.dumps(demo_summary), encoding="utf-8")
    manifest["checksums"]["openapi.json"] = export_release_artifacts.sha256_file(openapi_path)
    manifest["checksums"]["demo-summary.json"] = export_release_artifacts.sha256_file(artifact_dir / "demo-summary.json")
    manifest["checksums"]["release-manifest.json"] = export_release_artifacts.manifest_checksum(manifest)
    (artifact_dir / "release-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with zipfile.ZipFile(outside_package_path, mode="w") as archive:
        for artifact_path in sorted(artifact_dir.iterdir()):
            archive.write(artifact_path, arcname=artifact_path.name)

    report = validate_release_package.validate_release_package(package_path)

    assert report["ok"] is False
    assert f"release package parent is not a regular directory: {linked_root}" in report["issues"]
    assert linked_root.is_symlink()
    assert outside_package_path.exists()


def test_validate_release_package_rejects_windows_traversal_artifact_name(tmp_path):
    validate_release_package = load_validate_release_package()
    package_path = tmp_path / "paper-lab-agent-release.zip"
    with zipfile.ZipFile(package_path, mode="w") as archive:
        archive.writestr("demo-summary.json", "{}")
        archive.writestr("openapi.json", "{}")
        archive.writestr("release-manifest.json", "{}")
        archive.writestr("..\\evil.txt", "unsafe")

    report = validate_release_package.validate_release_package(package_path)

    assert report["ok"] is False
    assert "release package contains unsafe artifact names: ['..\\\\evil.txt']" in report["issues"]


def test_validate_release_package_rejects_windows_rooted_artifact_name(tmp_path):
    validate_release_package = load_validate_release_package()
    package_path = tmp_path / "paper-lab-agent-release.zip"
    with zipfile.ZipFile(package_path, mode="w") as archive:
        archive.writestr("demo-summary.json", "{}")
        archive.writestr("openapi.json", "{}")
        archive.writestr("release-manifest.json", "{}")
        archive.writestr("\\evil.txt", "unsafe")

    report = validate_release_package.validate_release_package(package_path)

    assert report["ok"] is False
    assert "release package contains unsafe artifact names: ['\\\\evil.txt']" in report["issues"]


def test_release_check_derives_expected_runtime_version_from_app_version():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert "from app import __version__" in release_text
    assert '"runtime_version": __version__' in release_text
    assert '"runtime_version": "0.1.0"' not in release_text


def test_release_check_requires_manual_resolve_oa_smoke_path():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"manual_resolve_oa_status": "green"' in release_text
    assert '"manual_resolve_oa_pdf_url"' in release_text
    assert '"paper_detail_has_raw_metadata": True' in release_text
    assert '"paper_detail_doi": "10.999/smoke-crawl"' in release_text
    assert '"journal_filter_search_hits": 1' in release_text
    assert '"oa_only_search_hits": 1' in release_text
    assert '"relevance_sort_search_hits": 1' in release_text
    assert '"year_filter_search_hits": 1' in release_text


def test_release_check_requires_crawl_job_observability_smoke_path():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"crawl_job_list_total": 1' in release_text
    assert '"crawl_job_detail_status": "success"' in release_text
    assert '"crawl_job_detail_journal_name": "Plasma Sources Science and Technology"' in release_text
    assert '"crawl_job_detail_diagnostics_outcome": "new_papers"' in release_text
    assert '"crawl_job_detail_diagnostics_papers_accepted": 3' in release_text
    assert '"crawl_job_detail_keyword_mode": "or"' in release_text
    assert '"crawl_job_detail_has_keyword_terms": True' in release_text
    assert '"crawl_job_detail_keyword_terms_include_plasma_chemistry": True' in release_text


def test_release_check_requires_no_doi_dedupe_smoke_path():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"crawl_job_found": 4' in release_text
    assert '"crawl_job_new": 2' in release_text
    assert '"no_doi_search_hits": 1' in release_text
    assert '"no_doi_paper_has_doi": False' in release_text
    assert '"no_doi_paper_dedupe_strategy": "no_doi_fingerprint"' in release_text
    assert '"no_doi_paper_has_dedupe_key": True' in release_text


def test_release_check_requires_document_list_and_detail_smoke_paths():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")
    smoke_text = (repo / "scripts" / "smoke_check.py").read_text(encoding="utf-8")

    assert '"document_list_total": 1' in release_text
    assert '"document_detail_parse_status": "uploaded"' in release_text
    assert '"document_detail_has_paper": True' in release_text
    assert '"duplicate_document_matches_original": True' in release_text
    assert '"duplicate_document_matches_original"' in smoke_text
    assert '"section_list_first_type": "body"' in release_text
    assert '"section_list_has_content": True' in release_text
    assert '"chunk_list_index_status": "indexed"' in release_text
    assert '"chunk_list_has_vector_id": True' in release_text
    assert '"chunk_list_has_section_title": True' in release_text


def test_release_check_requires_rag_source_locator_smoke_metadata():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"rag_source_has_document_id": True' in release_text
    assert '"rag_source_has_paper_id": True' in release_text
    assert '"rag_source_has_section_id": True' in release_text
    assert '"rag_source_has_section_title": True' in release_text
    assert '"rag_source_has_section_type": True' in release_text
    assert '"rag_source_has_chunk_id": True' in release_text
    assert '"rag_source_has_vector_id": True' in release_text
    assert '"rag_source_has_score": True' in release_text


def test_release_check_requires_manual_category_override_smoke_path():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"auto_classify_category_count": 1' in release_text
    assert '"auto_classify_method": "auto"' in release_text
    assert '"manual_category_method": "manual"' in release_text
    assert '"manual_category_count": 1' in release_text
    assert '"manual_category_search_hits": 1' in release_text


def test_release_check_requires_export_confidence_smoke_metadata():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"verified_export_txt_has_confidence": True' in release_text
    assert '"verified_export_bolsig_has_confidence": True' in release_text


def test_release_check_requires_export_source_label_smoke_metadata():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"verified_export_txt_has_source_label": True' in release_text
    assert '"verified_export_bolsig_has_source_label": True' in release_text


def test_release_check_requires_json_export_reviewer_audit_metadata():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")
    smoke_text = (repo / "scripts" / "smoke_check.py").read_text(encoding="utf-8")

    assert '"verified_export_has_smoke_check_audit": True' in release_text
    assert '"verified_export_has_smoke_check_audit"' in smoke_text


def test_release_check_requires_document_reaction_set_list_smoke_metadata():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"document_reaction_set_list_total": 1' in release_text
    assert '"document_reaction_set_reaction_count": 1' in release_text
    assert '"document_reaction_set_verified_count_before_verify": 0' in release_text
    assert '"document_reaction_set_unverified_count_before_verify": 1' in release_text
    assert '"document_reaction_set_export_ready_before_verify": False' in release_text
    assert '"document_reaction_set_export_ready_after_verify": True' in release_text


def test_release_check_requires_reaction_set_detail_smoke_metadata():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"reaction_set_detail_reaction_count_before_verify": 1' in release_text
    assert '"reaction_set_detail_verified_count_before_verify": 0' in release_text
    assert '"reaction_set_detail_unverified_count_before_verify": 1' in release_text
    assert '"reaction_set_detail_export_ready_before_verify": False' in release_text
    assert '"reaction_set_detail_export_ready_after_verify": True' in release_text
    assert '"reaction_set_detail_audit_entries_after_verify": 1' in release_text


def test_release_check_requires_reaction_type_smoke_metadata():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"extracted_reaction_type": "ionization"' in release_text
    assert '"verified_export_reaction_type": "ionization"' in release_text


def test_release_check_requires_rate_type_smoke_metadata():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"extracted_rate_type": "cross_section"' in release_text
    assert '"verified_export_rate_type": "cross_section"' in release_text


def test_release_check_rejects_failed_smoke_status_counts():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert "failed_statuses" in release_text
    assert "smoke failed statuses present" in release_text


def test_smoke_check_requires_error_response_shape_for_negative_paths():
    smoke_check = load_smoke_check()

    class Response:
        status_code = 409
        text = '{"document":{"id":1}}'

        def json(self):
            return {"document": {"id": 1}}

    try:
        smoke_check.assert_error_response(Response(), 409, "duplicate upload")
    except AssertionError as exc:
        assert "duplicate upload: expected error object" in str(exc)
    else:
        raise AssertionError("expected malformed error response to fail smoke validation")


def test_release_check_requires_smoke_error_response_coverage():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"error_response_count": 4' in release_text
    assert '"duplicate_upload_status": 409' in release_text
    assert '"unsupported_document_status": 415' in release_text
    assert '"blocked_export_status": 409' in release_text
    assert '"unsupported_export_status": 400' in release_text
    assert '"unsupported_document_type"' in release_text
    assert '"document_duplicate"' in release_text
    assert '"reaction_set_unverified"' in release_text
    assert '"unsupported_export_format"' in release_text


def test_release_check_requires_system_capability_smoke_metadata():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"system_translation_adapter": "local-echo"' in release_text
    assert '"system_embedding_model": "local-hash"' in release_text
    assert '"system_vector_db_backend": "local-json"' in release_text
    assert '"system_grobid_url": "http://127.0.0.1:8070"' in release_text


def test_release_check_requires_system_storage_health_smoke_metadata():
    repo = Path(__file__).resolve().parent.parent
    release_text = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert '"system_storage_data_dir_writable": True' in release_text
    assert '"system_storage_database_parent_writable": True' in release_text
    assert '"system_storage_vector_db_exists": True' in release_text
    assert '"system_storage_vector_db_valid_json": True' in release_text


def test_dev_script_documents_help_mode_without_starting_services():
    repo = Path(__file__).resolve().parent.parent
    dev_script = (repo / "scripts" / "dev.sh").read_text(encoding="utf-8")

    for required in [
        "--help",
        "Usage: bash scripts/dev.sh",
        "API_PORT",
        "STREAMLIT_PORT",
        "DEV_READY_TIMEOUT",
        "PAPER_LAB_SCHEDULER_ENABLED",
        "python scripts/health_check.py --require-frontend",
        "python scripts/health_check.py --require-openapi",
        "/openapi.json",
        "/docs",
        "/redoc",
    ]:
        assert required in dev_script


def test_api_contract_documented_endpoints_exist_in_app():
    validate_api_contract = load_validate_api_contract()
    repo = Path(__file__).resolve().parent.parent

    missing = validate_api_contract.missing_documented_routes(repo / "docs" / "接口设计文档.md")

    assert missing == []


def test_api_contract_app_routes_are_documented():
    validate_api_contract = load_validate_api_contract()
    repo = Path(__file__).resolve().parent.parent

    undocumented = validate_api_contract.undocumented_app_routes(repo / "docs" / "接口设计文档.md")

    assert undocumented == []


def test_api_contract_validator_reports_duplicate_documented_routes(tmp_path):
    validate_api_contract = load_validate_api_contract()
    repo = Path(__file__).resolve().parent.parent
    contract_path = tmp_path / "接口设计文档.md"
    contract_text = (repo / "docs" / "接口设计文档.md").read_text(encoding="utf-8")
    contract_path.write_text(
        contract_text + "\n| GET | `/health` | duplicate row |\n",
        encoding="utf-8",
    )

    duplicates = validate_api_contract.duplicate_documented_routes(contract_path)

    assert duplicates == ["GET /api/v1/health documented 2 times"]


def test_api_contract_app_routes_expose_openapi_tags():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.untagged_api_route_issues()

    assert issues == []


def test_api_contract_openapi_tags_have_metadata_descriptions():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.openapi_tag_metadata_issues()

    assert issues == []


def test_api_contract_documents_reaction_verify_reviewer_requirement():
    repo = Path(__file__).resolve().parent.parent
    contract_text = (repo / "docs" / "接口设计文档.md").read_text(encoding="utf-8")

    assert "verified_by` 必填且不能为空" in contract_text
    assert "缺失或空白返回 422 `validation_error`" in contract_text


def test_api_contract_validator_runs_as_release_script():
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent

    result = subprocess.run(
        [sys.executable, "scripts/validate_api_contract.py"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_api_contract_validator_reports_documented_route_missing_from_app(tmp_path):
    validate_api_contract = load_validate_api_contract()
    repo = Path(__file__).resolve().parent.parent
    contract_path = tmp_path / "接口设计文档.md"
    contract_text = (repo / "docs" / "接口设计文档.md").read_text(encoding="utf-8")
    contract_path.write_text(
        contract_text + "\n| GET | `/nonexistent-release-contract-route` | should fail |\n",
        encoding="utf-8",
    )

    missing = validate_api_contract.missing_documented_routes(contract_path)

    assert missing == ["GET /api/v1/nonexistent-release-contract-route"]


def test_api_contract_paginated_get_routes_expose_page_parameters():
    validate_api_contract = load_validate_api_contract()
    repo = Path(__file__).resolve().parent.parent

    issues = validate_api_contract.pagination_contract_issues(repo / "docs" / "接口设计文档.md")

    assert issues == []


def test_api_contract_paginated_get_routes_expose_response_shape():
    validate_api_contract = load_validate_api_contract()
    repo = Path(__file__).resolve().parent.parent

    issues = validate_api_contract.pagination_response_contract_issues(repo / "docs" / "接口设计文档.md")

    assert issues == []


def test_api_contract_validator_reports_missing_paginated_response_field(tmp_path):
    validate_api_contract = load_validate_api_contract()
    contract_path = tmp_path / "接口设计文档.md"
    contract_path.write_text("| GET | `/things` | 列出测试资源 |\n", encoding="utf-8")
    openapi_paths = {
        "/api/v1/things": {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["items", "total", "page"],
                                    "properties": {
                                        "items": {"type": "array", "items": {"type": "object"}},
                                        "total": {"type": "integer"},
                                        "page": {"type": "integer"},
                                    },
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.pagination_response_contract_issues(contract_path, openapi_paths=openapi_paths)

    assert issues == ["GET /api/v1/things missing response fields: page_size"]


def test_api_contract_validator_reports_missing_page_size_on_documented_list_route(tmp_path):
    validate_api_contract = load_validate_api_contract()
    contract_path = tmp_path / "接口设计文档.md"
    contract_path.write_text("| GET | `/things` | 列出测试资源 |\n", encoding="utf-8")
    openapi_paths = {
        "/api/v1/things": {
            "get": {
                "parameters": [
                    {"name": "page", "in": "query", "schema": {"default": 1}},
                ]
            }
        }
    }

    issues = validate_api_contract.pagination_contract_issues(contract_path, openapi_paths=openapi_paths)

    assert issues == ["GET /api/v1/things missing query parameters: page_size"]


def test_api_contract_async_routes_expose_accepted_response():
    validate_api_contract = load_validate_api_contract()
    repo = Path(__file__).resolve().parent.parent

    issues = validate_api_contract.async_response_contract_issues(repo / "docs" / "接口设计文档.md")

    assert issues == []


def test_api_contract_async_routes_expose_pending_response_shape():
    validate_api_contract = load_validate_api_contract()
    repo = Path(__file__).resolve().parent.parent

    issues = validate_api_contract.async_response_body_contract_issues(repo / "docs" / "接口设计文档.md")

    assert issues == []


def test_api_contract_success_responses_do_not_use_empty_generic_schema():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.empty_success_response_schema_issues()

    assert issues == []


def test_api_contract_success_responses_do_not_use_bare_dict_schema():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.bare_success_response_schema_issues()

    assert issues == []


def test_api_contract_success_responses_use_named_component_schemas():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.named_success_response_schema_issues()

    assert issues == []


def test_api_contract_validator_reports_empty_success_response_schema():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/crawl/run": {
                "post": {
                    "responses": {
                        "202": {
                            "content": {
                                "application/json": {
                                    "schema": {},
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.empty_success_response_schema_issues(openapi=openapi)

    assert issues == ["POST /api/v1/crawl/run 202 response must declare a non-empty schema"]


def test_api_contract_validator_reports_bare_success_response_schema():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/things": {
                "post": {
                    "responses": {
                        "201": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "additionalProperties": True,
                                    },
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.bare_success_response_schema_issues(openapi=openapi)

    assert issues == ["POST /api/v1/things 201 response must not use a bare dict schema"]


def test_api_contract_validator_reports_inline_success_response_schema():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/things": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["id"],
                                        "properties": {"id": {"type": "integer"}},
                                    },
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.named_success_response_schema_issues(openapi=openapi)

    assert issues == ["GET /api/v1/things 200 response must use a named component schema"]


def test_api_contract_validator_reports_untagged_api_route():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/things": {
                "get": {
                    "responses": {"200": {"description": "OK"}},
                }
            }
        }
    }

    issues = validate_api_contract.untagged_api_route_issues(openapi=openapi)

    assert issues == ["GET /api/v1/things missing OpenAPI tags"]


def test_api_contract_validator_reports_missing_openapi_tag_metadata():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/things": {
                "get": {
                    "tags": ["things"],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
        "tags": [],
    }

    issues = validate_api_contract.openapi_tag_metadata_issues(openapi=openapi)

    assert issues == ["OpenAPI tag metadata missing: things"]


def test_api_contract_validator_reports_openapi_tag_metadata_missing_description():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/things": {
                "get": {
                    "tags": ["things"],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
        "tags": [{"name": "things"}],
    }

    issues = validate_api_contract.openapi_tag_metadata_issues(openapi=openapi)

    assert issues == ["OpenAPI tag metadata missing descriptions: things"]


def test_api_contract_validator_reports_missing_async_response_field(tmp_path):
    validate_api_contract = load_validate_api_contract()
    contract_path = tmp_path / "接口设计文档.md"
    contract_path.write_text("| POST | `/documents/{id}/parse` | 触发 GROBID 解析 |\n", encoding="utf-8")
    openapi_paths = {
        "/api/v1/documents/{document_id}/parse": {
            "post": {
                "responses": {
                    "202": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["job_id"],
                                    "properties": {"job_id": {"type": "integer"}},
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.async_response_body_contract_issues(contract_path, openapi_paths=openapi_paths)

    assert issues == ["POST /api/v1/documents/{id}/parse missing 202 response fields: status"]


def test_api_contract_error_responses_expose_unified_shape():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.error_response_contract_issues()

    assert issues == []


def test_api_contract_semantic_error_statuses_are_documented():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.semantic_error_status_contract_issues()

    assert issues == []


def test_api_contract_health_response_exposes_probe_metadata():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.health_response_contract_issues()

    assert issues == []


def test_api_contract_validator_reports_missing_health_response_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/health": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["status"],
                                        "properties": {"status": {"type": "string"}},
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.health_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/health missing response fields: service"]


def test_api_contract_journal_list_response_exposes_typed_whitelist_items():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.journal_list_response_contract_issues()

    assert issues == []


def test_api_contract_journal_crud_responses_expose_typed_whitelist_items():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.journal_crud_response_contract_issues()

    assert issues == []


def test_api_contract_category_list_response_exposes_typed_tree_items():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.category_list_response_contract_issues()

    assert issues == []


def test_api_contract_category_create_response_exposes_typed_tree_item():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.category_create_response_contract_issues()

    assert issues == []


def test_api_contract_validator_reports_missing_category_list_item_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/categories": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["items", "total", "page", "page_size"],
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "id",
                                                        "name",
                                                        "slug",
                                                        "description",
                                                        "parent_id",
                                                    ],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "name": {"type": "string"},
                                                        "slug": {"type": "string"},
                                                        "description": {"type": "string"},
                                                        "parent_id": {"type": "integer"},
                                                    },
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "page": {"type": "integer"},
                                            "page_size": {"type": "integer"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.category_list_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/categories item fields missing: children"]


def test_api_contract_validator_reports_missing_category_child_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/categories": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["items", "total", "page", "page_size"],
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "id",
                                                        "name",
                                                        "slug",
                                                        "description",
                                                        "parent_id",
                                                        "children",
                                                    ],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "name": {"type": "string"},
                                                        "slug": {"type": "string"},
                                                        "description": {"type": "string"},
                                                        "parent_id": {"type": "integer"},
                                                        "children": {
                                                            "type": "array",
                                                            "items": {
                                                                "type": "object",
                                                                "required": ["id", "name", "slug", "description"],
                                                                "properties": {
                                                                    "id": {"type": "integer"},
                                                                    "name": {"type": "string"},
                                                                    "slug": {"type": "string"},
                                                                    "description": {"type": "string"},
                                                                },
                                                            },
                                                        },
                                                    },
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "page": {"type": "integer"},
                                            "page_size": {"type": "integer"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.category_list_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/categories item child fields missing: parent_id, children"]


def test_api_contract_validator_reports_missing_category_create_response_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/categories": {
                "post": {
                    "responses": {
                        "201": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["id", "name", "slug", "description", "parent_id"],
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                            "slug": {"type": "string"},
                                            "description": {"type": "string"},
                                            "parent_id": {"type": "integer"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.category_create_response_contract_issues(openapi=openapi)

    assert issues == ["POST /api/v1/categories missing response fields: children"]


def test_api_contract_validator_reports_missing_journal_list_item_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/journals": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["items", "total", "page", "page_size"],
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "id",
                                                        "name",
                                                        "publisher",
                                                        "platform",
                                                        "url",
                                                        "issn_print",
                                                        "issn_electronic",
                                                        "keywords",
                                                        "year_from",
                                                        "year_to",
                                                        "sci_zone",
                                                        "impact_factor",
                                                        "active",
                                                        "created_at",
                                                    ],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "name": {"type": "string"},
                                                        "publisher": {"type": "string"},
                                                        "platform": {"type": "string"},
                                                        "url": {"type": "string"},
                                                        "issn_print": {"type": "string"},
                                                        "issn_electronic": {"type": "string"},
                                                        "keywords": {"type": "array"},
                                                        "year_from": {"type": "integer"},
                                                        "year_to": {"type": "integer"},
                                                        "sci_zone": {"type": "string"},
                                                        "impact_factor": {"type": "number"},
                                                        "active": {"type": "boolean"},
                                                        "created_at": {"type": "string"},
                                                    },
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "page": {"type": "integer"},
                                            "page_size": {"type": "integer"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.journal_list_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/journals item fields missing: updated_at"]


def test_api_contract_validator_reports_missing_journal_crud_response_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/journals/{journal_id}": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "id",
                                            "name",
                                            "publisher",
                                            "platform",
                                            "url",
                                            "issn_print",
                                            "issn_electronic",
                                            "keywords",
                                            "year_from",
                                            "year_to",
                                            "sci_zone",
                                            "impact_factor",
                                            "active",
                                            "created_at",
                                        ],
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                            "publisher": {"type": "string"},
                                            "platform": {"type": "string"},
                                            "url": {"type": "string"},
                                            "issn_print": {"type": "string"},
                                            "issn_electronic": {"type": "string"},
                                            "keywords": {"type": "array"},
                                            "year_from": {"type": "integer"},
                                            "year_to": {"type": "integer"},
                                            "sci_zone": {"type": "string"},
                                            "impact_factor": {"type": "number"},
                                            "active": {"type": "boolean"},
                                            "created_at": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.journal_crud_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/journals/{} missing response fields: updated_at"]


def test_api_contract_export_response_exposes_delivery_metadata():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.export_response_contract_issues()

    assert issues == []


def test_api_contract_reaction_set_list_response_exposes_typed_review_items():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.reaction_set_list_response_contract_issues()

    assert issues == []


def test_api_contract_validator_reports_missing_reaction_set_list_item_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/documents/{document_id}/reaction-sets": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["items", "total", "page", "page_size"],
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "id",
                                                        "document_id",
                                                        "name",
                                                        "gas_mixture",
                                                        "lxcat_db",
                                                        "source_note",
                                                        "status",
                                                        "verified_by",
                                                        "verified_at",
                                                        "created_at",
                                                        "reaction_count",
                                                        "verified_count",
                                                        "unverified_count",
                                                    ],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "document_id": {"type": "integer"},
                                                        "name": {"type": "string"},
                                                        "gas_mixture": {"type": "string"},
                                                        "lxcat_db": {"type": "string"},
                                                        "source_note": {"type": "string"},
                                                        "status": {"type": "string"},
                                                        "verified_by": {"type": "string"},
                                                        "verified_at": {"type": "string"},
                                                        "created_at": {"type": "string"},
                                                        "reaction_count": {"type": "integer"},
                                                        "verified_count": {"type": "integer"},
                                                        "unverified_count": {"type": "integer"},
                                                    },
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "page": {"type": "integer"},
                                            "page_size": {"type": "integer"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.reaction_set_list_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/documents/{}/reaction-sets item fields missing: export_ready"]


def test_api_contract_document_responses_expose_associated_paper_summary():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.document_response_contract_issues()

    assert issues == []


def test_api_contract_document_list_response_exposes_typed_document_items():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.document_list_response_contract_issues()

    assert issues == []


def test_api_contract_section_list_response_exposes_typed_section_items():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.section_list_response_contract_issues()

    assert issues == []


def test_api_contract_chunk_list_response_exposes_typed_index_items():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.chunk_list_response_contract_issues()

    assert issues == []


def test_api_contract_validator_reports_missing_chunk_list_response_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/documents/{document_id}/chunks": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "items",
                                            "total",
                                            "page",
                                            "page_size",
                                            "indexed",
                                            "index_status",
                                        ],
                                        "properties": {
                                            "items": {"type": "array", "items": {"type": "object"}},
                                            "total": {"type": "integer"},
                                            "page": {"type": "integer"},
                                            "page_size": {"type": "integer"},
                                            "indexed": {"type": "boolean"},
                                            "index_status": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.chunk_list_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/documents/{}/chunks missing response fields: index_error"]


def test_api_contract_validator_reports_missing_chunk_list_item_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/documents/{document_id}/chunks": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "items",
                                            "total",
                                            "page",
                                            "page_size",
                                            "indexed",
                                            "index_status",
                                            "index_error",
                                        ],
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "id",
                                                        "document_id",
                                                        "section_id",
                                                        "seq",
                                                        "text",
                                                        "token_count",
                                                        "vector_id",
                                                        "embedded",
                                                        "created_at",
                                                    ],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "document_id": {"type": "integer"},
                                                        "section_id": {"type": "integer"},
                                                        "seq": {"type": "integer"},
                                                        "text": {"type": "string"},
                                                        "token_count": {"type": "integer"},
                                                        "vector_id": {"type": "string"},
                                                        "embedded": {"type": "boolean"},
                                                        "created_at": {"type": "string"},
                                                    },
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "page": {"type": "integer"},
                                            "page_size": {"type": "integer"},
                                            "indexed": {"type": "boolean"},
                                            "index_status": {"type": "string"},
                                            "index_error": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.chunk_list_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/documents/{}/chunks item fields missing: section_title"]


def test_api_contract_validator_reports_missing_section_list_item_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/documents/{document_id}/sections": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["items", "total", "page", "page_size"],
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "id",
                                                        "document_id",
                                                        "parent_id",
                                                        "seq",
                                                        "title",
                                                        "content",
                                                    ],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "document_id": {"type": "integer"},
                                                        "parent_id": {"type": "integer"},
                                                        "seq": {"type": "integer"},
                                                        "title": {"type": "string"},
                                                        "content": {"type": "string"},
                                                    },
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "page": {"type": "integer"},
                                            "page_size": {"type": "integer"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.section_list_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/documents/{}/sections item fields missing: section_type"]


def test_api_contract_validator_reports_missing_document_list_item_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/documents": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["items", "total", "page", "page_size"],
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "id",
                                                        "paper_id",
                                                        "file_path",
                                                        "file_hash",
                                                        "original_name",
                                                        "num_pages",
                                                        "parse_status",
                                                        "parse_error",
                                                        "index_status",
                                                        "index_error",
                                                        "chemistry_status",
                                                        "chemistry_error",
                                                        "tei_path",
                                                        "created_at",
                                                    ],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "paper_id": {"type": "integer"},
                                                        "file_path": {"type": "string"},
                                                        "file_hash": {"type": "string"},
                                                        "original_name": {"type": "string"},
                                                        "num_pages": {"type": "integer"},
                                                        "parse_status": {"type": "string"},
                                                        "parse_error": {"type": "string"},
                                                        "index_status": {"type": "string"},
                                                        "index_error": {"type": "string"},
                                                        "chemistry_status": {"type": "string"},
                                                        "chemistry_error": {"type": "string"},
                                                        "tei_path": {"type": "string"},
                                                        "created_at": {"type": "string"},
                                                    },
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "page": {"type": "integer"},
                                            "page_size": {"type": "integer"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.document_list_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/documents item fields missing: paper"]


def test_api_contract_validator_reports_missing_document_list_paper_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/documents": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["items", "total", "page", "page_size"],
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "id",
                                                        "paper_id",
                                                        "file_path",
                                                        "file_hash",
                                                        "original_name",
                                                        "num_pages",
                                                        "parse_status",
                                                        "parse_error",
                                                        "index_status",
                                                        "index_error",
                                                        "chemistry_status",
                                                        "chemistry_error",
                                                        "tei_path",
                                                        "created_at",
                                                        "paper",
                                                    ],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "paper_id": {"type": "integer"},
                                                        "file_path": {"type": "string"},
                                                        "file_hash": {"type": "string"},
                                                        "original_name": {"type": "string"},
                                                        "num_pages": {"type": "integer"},
                                                        "parse_status": {"type": "string"},
                                                        "parse_error": {"type": "string"},
                                                        "index_status": {"type": "string"},
                                                        "index_error": {"type": "string"},
                                                        "chemistry_status": {"type": "string"},
                                                        "chemistry_error": {"type": "string"},
                                                        "tei_path": {"type": "string"},
                                                        "created_at": {"type": "string"},
                                                        "paper": {
                                                            "type": "object",
                                                            "required": ["id", "doi", "title", "journal_name"],
                                                            "properties": {
                                                                "id": {"type": "integer"},
                                                                "doi": {"type": "string"},
                                                                "title": {"type": "string"},
                                                                "journal_name": {"type": "string"},
                                                            },
                                                        },
                                                    },
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "page": {"type": "integer"},
                                            "page_size": {"type": "integer"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.document_list_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/documents item paper fields missing: published_date"]


def test_api_contract_translation_response_exposes_status_and_output_path():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.translation_response_contract_issues()

    assert issues == []


def test_api_contract_paper_detail_response_exposes_metadata_and_categories():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.paper_detail_response_contract_issues()

    assert issues == []


def test_api_contract_paper_mutation_responses_expose_metadata_and_categories():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.paper_mutation_response_contract_issues()

    assert issues == []


def test_api_contract_paper_list_response_exposes_typed_search_items():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.paper_list_response_contract_issues()

    assert issues == []


def test_api_contract_validator_reports_missing_paper_list_item_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/papers": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["items", "total", "page", "page_size"],
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "id",
                                                        "doi",
                                                        "title",
                                                        "abstract",
                                                        "authors",
                                                        "journal_id",
                                                        "journal_name",
                                                        "published_date",
                                                        "published_year",
                                                        "oa_status",
                                                        "oa_pdf_url",
                                                        "landing_url",
                                                        "source_api",
                                                        "dedupe_key",
                                                        "has_doi",
                                                        "dedupe_strategy",
                                                        "categories",
                                                    ],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "doi": {"type": "string"},
                                                        "title": {"type": "string"},
                                                        "abstract": {"type": "string"},
                                                        "authors": {"type": "array"},
                                                        "journal_id": {"type": "integer"},
                                                        "journal_name": {"type": "string"},
                                                        "published_date": {"type": "string"},
                                                        "published_year": {"type": "integer"},
                                                        "oa_status": {"type": "string"},
                                                        "oa_pdf_url": {"type": "string"},
                                                        "landing_url": {"type": "string"},
                                                        "source_api": {"type": "string"},
                                                        "dedupe_key": {"type": "string"},
                                                        "has_doi": {"type": "boolean"},
                                                        "dedupe_strategy": {"type": "string"},
                                                        "categories": {"type": "array"},
                                                    },
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "page": {"type": "integer"},
                                            "page_size": {"type": "integer"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.paper_list_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/papers item fields missing: category_details"]


def test_api_contract_validator_reports_missing_paper_list_category_detail_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/papers": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["items", "total", "page", "page_size"],
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "id",
                                                        "doi",
                                                        "title",
                                                        "abstract",
                                                        "authors",
                                                        "journal_id",
                                                        "journal_name",
                                                        "published_date",
                                                        "published_year",
                                                        "oa_status",
                                                        "oa_pdf_url",
                                                        "landing_url",
                                                        "source_api",
                                                        "dedupe_key",
                                                        "has_doi",
                                                        "dedupe_strategy",
                                                        "categories",
                                                        "category_details",
                                                    ],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "doi": {"type": "string"},
                                                        "title": {"type": "string"},
                                                        "abstract": {"type": "string"},
                                                        "authors": {"type": "array"},
                                                        "journal_id": {"type": "integer"},
                                                        "journal_name": {"type": "string"},
                                                        "published_date": {"type": "string"},
                                                        "published_year": {"type": "integer"},
                                                        "oa_status": {"type": "string"},
                                                        "oa_pdf_url": {"type": "string"},
                                                        "landing_url": {"type": "string"},
                                                        "source_api": {"type": "string"},
                                                        "dedupe_key": {"type": "string"},
                                                        "has_doi": {"type": "boolean"},
                                                        "dedupe_strategy": {"type": "string"},
                                                        "categories": {"type": "array"},
                                                        "category_details": {
                                                            "type": "array",
                                                            "items": {
                                                                "type": "object",
                                                                "required": ["id", "slug", "name", "confidence"],
                                                                "properties": {
                                                                    "id": {"type": "integer"},
                                                                    "slug": {"type": "string"},
                                                                    "name": {"type": "string"},
                                                                    "confidence": {"type": "number"},
                                                                },
                                                            },
                                                        },
                                                    },
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "page": {"type": "integer"},
                                            "page_size": {"type": "integer"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.paper_list_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/papers item category detail fields missing: method"]


def test_api_contract_crawl_job_detail_response_exposes_diagnostics():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.crawl_job_detail_response_contract_issues()

    assert issues == []


def test_api_contract_crawl_job_list_response_exposes_typed_diagnostic_items():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.crawl_job_list_response_contract_issues()

    assert issues == []


def test_api_contract_validator_reports_missing_crawl_job_list_item_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/crawl/jobs": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["items", "total", "page", "page_size"],
                                        "properties": {
                                            "items": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "id",
                                                        "journal_id",
                                                        "period",
                                                        "date_from",
                                                        "date_to",
                                                        "status",
                                                        "papers_found",
                                                        "papers_filtered",
                                                        "papers_new",
                                                        "error",
                                                        "started_at",
                                                        "finished_at",
                                                        "created_at",
                                                        "journal",
                                                    ],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "journal_id": {"type": "integer"},
                                                        "period": {"type": "string"},
                                                        "date_from": {"type": "string"},
                                                        "date_to": {"type": "string"},
                                                        "status": {"type": "string"},
                                                        "papers_found": {"type": "integer"},
                                                        "papers_filtered": {"type": "integer"},
                                                        "papers_new": {"type": "integer"},
                                                        "error": {"type": "string"},
                                                        "started_at": {"type": "string"},
                                                        "finished_at": {"type": "string"},
                                                        "created_at": {"type": "string"},
                                                        "journal": {"type": "object"},
                                                    },
                                                },
                                            },
                                            "total": {"type": "integer"},
                                            "page": {"type": "integer"},
                                            "page_size": {"type": "integer"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.crawl_job_list_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/crawl/jobs item fields missing: diagnostics"]


def test_api_contract_validator_reports_missing_crawl_job_detail_response_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/crawl/jobs/{job_id}": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "id",
                                            "journal_id",
                                            "period",
                                            "date_from",
                                            "date_to",
                                            "status",
                                            "papers_found",
                                            "papers_filtered",
                                            "papers_new",
                                            "error",
                                            "started_at",
                                            "finished_at",
                                            "created_at",
                                            "journal",
                                        ],
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "journal_id": {"type": "integer"},
                                            "period": {"type": "string"},
                                            "date_from": {"type": "string"},
                                            "date_to": {"type": "string"},
                                            "status": {"type": "string"},
                                            "papers_found": {"type": "integer"},
                                            "papers_filtered": {"type": "integer"},
                                            "papers_new": {"type": "integer"},
                                            "error": {"type": "string"},
                                            "started_at": {"type": "string"},
                                            "finished_at": {"type": "string"},
                                            "created_at": {"type": "string"},
                                            "journal": {
                                                "type": "object",
                                                "required": [
                                                    "id",
                                                    "name",
                                                    "issn_print",
                                                    "issn_electronic",
                                                    "active",
                                                ],
                                                "properties": {
                                                    "id": {"type": "integer"},
                                                    "name": {"type": "string"},
                                                    "issn_print": {"type": "string"},
                                                    "issn_electronic": {"type": "string"},
                                                    "active": {"type": "boolean"},
                                                },
                                            },
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.crawl_job_detail_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/crawl/jobs/{} missing response fields: diagnostics"]


def test_api_contract_validator_reports_missing_crawl_job_diagnostic_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/crawl/jobs/{job_id}": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "id",
                                            "journal_id",
                                            "period",
                                            "date_from",
                                            "date_to",
                                            "status",
                                            "papers_found",
                                            "papers_filtered",
                                            "papers_new",
                                            "error",
                                            "started_at",
                                            "finished_at",
                                            "created_at",
                                            "journal",
                                            "diagnostics",
                                        ],
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "journal_id": {"type": "integer"},
                                            "period": {"type": "string"},
                                            "date_from": {"type": "string"},
                                            "date_to": {"type": "string"},
                                            "status": {"type": "string"},
                                            "papers_found": {"type": "integer"},
                                            "papers_filtered": {"type": "integer"},
                                            "papers_new": {"type": "integer"},
                                            "error": {"type": "string"},
                                            "started_at": {"type": "string"},
                                            "finished_at": {"type": "string"},
                                            "created_at": {"type": "string"},
                                            "journal": {
                                                "type": "object",
                                                "required": [
                                                    "id",
                                                    "name",
                                                    "issn_print",
                                                    "issn_electronic",
                                                    "active",
                                                ],
                                                "properties": {
                                                    "id": {"type": "integer"},
                                                    "name": {"type": "string"},
                                                    "issn_print": {"type": "string"},
                                                    "issn_electronic": {"type": "string"},
                                                    "active": {"type": "boolean"},
                                                },
                                            },
                                            "diagnostics": {
                                                "type": "object",
                                                "required": [
                                                    "journal_id",
                                                    "journal_name",
                                                    "period",
                                                    "date_from",
                                                    "date_to",
                                                    "status",
                                                    "papers_found",
                                                    "papers_filtered",
                                                    "papers_new",
                                                    "papers_accepted",
                                                    "papers_existing",
                                                    "outcome",
                                                    "keyword_mode",
                                                    "error",
                                                ],
                                                "properties": {
                                                    "journal_id": {"type": "integer"},
                                                    "journal_name": {"type": "string"},
                                                    "period": {"type": "string"},
                                                    "date_from": {"type": "string"},
                                                    "date_to": {"type": "string"},
                                                    "status": {"type": "string"},
                                                    "papers_found": {"type": "integer"},
                                                    "papers_filtered": {"type": "integer"},
                                                    "papers_new": {"type": "integer"},
                                                    "papers_accepted": {"type": "integer"},
                                                    "papers_existing": {"type": "integer"},
                                                    "outcome": {"type": "string"},
                                                    "keyword_mode": {"type": "string"},
                                                    "error": {"type": "string"},
                                                },
                                            },
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.crawl_job_detail_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/crawl/jobs/{} diagnostics fields missing: keyword_terms"]


def test_api_contract_validator_reports_missing_paper_detail_response_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/papers/{paper_id}": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "id",
                                            "doi",
                                            "title",
                                            "abstract",
                                            "authors",
                                            "journal_id",
                                            "journal_name",
                                            "published_date",
                                            "published_year",
                                            "oa_status",
                                            "oa_pdf_url",
                                            "landing_url",
                                            "source_api",
                                            "dedupe_key",
                                            "has_doi",
                                            "dedupe_strategy",
                                            "categories",
                                            "category_details",
                                        ],
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "doi": {"type": "string"},
                                            "title": {"type": "string"},
                                            "abstract": {"type": "string"},
                                            "authors": {"type": "array"},
                                            "journal_id": {"type": "integer"},
                                            "journal_name": {"type": "string"},
                                            "published_date": {"type": "string"},
                                            "published_year": {"type": "integer"},
                                            "oa_status": {"type": "string"},
                                            "oa_pdf_url": {"type": "string"},
                                            "landing_url": {"type": "string"},
                                            "source_api": {"type": "string"},
                                            "dedupe_key": {"type": "string"},
                                            "has_doi": {"type": "boolean"},
                                            "dedupe_strategy": {"type": "string"},
                                            "categories": {"type": "array"},
                                            "category_details": {"type": "array", "items": {"type": "object"}},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.paper_detail_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/papers/{} missing response fields: raw_metadata"]


def test_api_contract_validator_reports_missing_paper_mutation_response_field():
    validate_api_contract = load_validate_api_contract()
    response_fields = [
        field for field in validate_api_contract.PAPER_DETAIL_RESPONSE_FIELDS if field != "raw_metadata"
    ]
    schema = {
        "type": "object",
        "required": response_fields,
        "properties": {field: {"type": "string"} for field in response_fields},
    }
    schema["properties"]["category_details"] = {
        "type": "array",
        "items": {
            "type": "object",
            "required": list(validate_api_contract.PAPER_CATEGORY_DETAIL_FIELDS),
            "properties": {
                field: {"type": "string"} for field in validate_api_contract.PAPER_CATEGORY_DETAIL_FIELDS
            },
        },
    }
    openapi = {
        "paths": {
            "/api/v1/papers/{paper_id}/classify": {
                "post": {
                    "responses": {
                        "200": {
                            "content": {"application/json": {"schema": schema}},
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.paper_mutation_response_contract_issues(openapi=openapi)

    assert issues == ["POST /api/v1/papers/{}/classify missing response fields: raw_metadata"]


def test_api_contract_validator_reports_missing_paper_category_detail_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/papers/{paper_id}": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "id",
                                            "doi",
                                            "title",
                                            "abstract",
                                            "authors",
                                            "journal_id",
                                            "journal_name",
                                            "published_date",
                                            "published_year",
                                            "oa_status",
                                            "oa_pdf_url",
                                            "landing_url",
                                            "source_api",
                                            "dedupe_key",
                                            "has_doi",
                                            "dedupe_strategy",
                                            "categories",
                                            "category_details",
                                            "raw_metadata",
                                        ],
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "doi": {"type": "string"},
                                            "title": {"type": "string"},
                                            "abstract": {"type": "string"},
                                            "authors": {"type": "array"},
                                            "journal_id": {"type": "integer"},
                                            "journal_name": {"type": "string"},
                                            "published_date": {"type": "string"},
                                            "published_year": {"type": "integer"},
                                            "oa_status": {"type": "string"},
                                            "oa_pdf_url": {"type": "string"},
                                            "landing_url": {"type": "string"},
                                            "source_api": {"type": "string"},
                                            "dedupe_key": {"type": "string"},
                                            "has_doi": {"type": "boolean"},
                                            "dedupe_strategy": {"type": "string"},
                                            "categories": {"type": "array"},
                                            "raw_metadata": {"type": "object"},
                                            "category_details": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": ["id", "slug", "name", "confidence"],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "slug": {"type": "string"},
                                                        "name": {"type": "string"},
                                                        "confidence": {"type": "number"},
                                                    },
                                                },
                                            },
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.paper_detail_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/papers/{} category detail fields missing: method"]


def test_api_contract_validator_reports_missing_translation_response_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/documents/{document_id}/translation": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "id",
                                            "document_id",
                                            "source_lang",
                                            "target_lang",
                                            "status",
                                            "error",
                                            "created_at",
                                        ],
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "document_id": {"type": "integer"},
                                            "source_lang": {"type": "string"},
                                            "target_lang": {"type": "string"},
                                            "status": {"type": "string"},
                                            "error": {"type": "string"},
                                            "created_at": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.translation_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/documents/{}/translation missing response fields: output_path"]


def test_api_contract_validator_reports_missing_document_response_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/documents/{document_id}": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "id",
                                            "paper_id",
                                            "file_path",
                                            "file_hash",
                                            "original_name",
                                            "num_pages",
                                            "parse_status",
                                            "parse_error",
                                            "index_status",
                                            "index_error",
                                            "chemistry_status",
                                            "chemistry_error",
                                            "tei_path",
                                            "created_at",
                                        ],
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "paper_id": {"type": "integer"},
                                            "file_path": {"type": "string"},
                                            "file_hash": {"type": "string"},
                                            "original_name": {"type": "string"},
                                            "num_pages": {"type": "integer"},
                                            "parse_status": {"type": "string"},
                                            "parse_error": {"type": "string"},
                                            "index_status": {"type": "string"},
                                            "index_error": {"type": "string"},
                                            "chemistry_status": {"type": "string"},
                                            "chemistry_error": {"type": "string"},
                                            "tei_path": {"type": "string"},
                                            "created_at": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/v1/documents": {
                "post": {
                    "responses": {
                        "201": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["id", "paper"],
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "paper": {"type": "object"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            },
        }
    }

    issues = validate_api_contract.document_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/documents/{} missing response fields: paper"]


def test_api_contract_validator_reports_missing_document_paper_field():
    validate_api_contract = load_validate_api_contract()
    document_schema = {
        "type": "object",
        "required": [
            "id",
            "paper_id",
            "file_path",
            "file_hash",
            "original_name",
            "num_pages",
            "parse_status",
            "parse_error",
            "index_status",
            "index_error",
            "chemistry_status",
            "chemistry_error",
            "tei_path",
            "created_at",
            "paper",
        ],
        "properties": {
            "id": {"type": "integer"},
            "paper_id": {"type": "integer"},
            "file_path": {"type": "string"},
            "file_hash": {"type": "string"},
            "original_name": {"type": "string"},
            "num_pages": {"type": "integer"},
            "parse_status": {"type": "string"},
            "parse_error": {"type": "string"},
            "index_status": {"type": "string"},
            "index_error": {"type": "string"},
            "chemistry_status": {"type": "string"},
            "chemistry_error": {"type": "string"},
            "tei_path": {"type": "string"},
            "created_at": {"type": "string"},
            "paper": {
                "type": "object",
                "required": ["id", "doi", "title", "journal_name"],
                "properties": {
                    "id": {"type": "integer"},
                    "doi": {"type": "string"},
                    "title": {"type": "string"},
                    "journal_name": {"type": "string"},
                },
            },
        },
    }
    openapi = {
        "paths": {
            "/api/v1/documents/{document_id}": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {"application/json": {"schema": document_schema}},
                        }
                    }
                }
            },
            "/api/v1/documents": {
                "post": {
                    "responses": {
                        "201": {
                            "content": {"application/json": {"schema": document_schema}},
                        }
                    }
                }
            },
        }
    }

    issues = validate_api_contract.document_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/documents/{} paper fields missing: published_date"]


def test_api_contract_reaction_set_detail_response_exposes_review_gate():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.reaction_set_detail_response_contract_issues()

    assert issues == []


def test_api_contract_reaction_verify_response_exposes_review_gate():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.reaction_verify_response_contract_issues()

    assert issues == []


def test_api_contract_validator_reports_missing_reaction_set_detail_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/reaction-sets/{reaction_set_id}": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "id",
                                            "document_id",
                                            "name",
                                            "gas_mixture",
                                            "lxcat_db",
                                            "source_note",
                                            "status",
                                            "created_at",
                                            "reactions",
                                            "reaction_count",
                                            "verified_count",
                                            "unverified_count",
                                        ],
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "document_id": {"type": "integer"},
                                            "name": {"type": "string"},
                                            "gas_mixture": {"type": "string"},
                                            "lxcat_db": {"type": "string"},
                                            "source_note": {"type": "string"},
                                            "status": {"type": "string"},
                                            "created_at": {"type": "string"},
                                            "reactions": {"type": "array", "items": {"type": "object"}},
                                            "reaction_count": {"type": "integer"},
                                            "verified_count": {"type": "integer"},
                                            "unverified_count": {"type": "integer"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.reaction_set_detail_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/reaction-sets/{} missing response fields: export_ready"]


def test_api_contract_validator_reports_missing_reaction_set_detail_reaction_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/reaction-sets/{reaction_set_id}": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "id",
                                            "document_id",
                                            "name",
                                            "gas_mixture",
                                            "lxcat_db",
                                            "source_note",
                                            "status",
                                            "created_at",
                                            "reactions",
                                            "reaction_count",
                                            "verified_count",
                                            "unverified_count",
                                            "export_ready",
                                        ],
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "document_id": {"type": "integer"},
                                            "name": {"type": "string"},
                                            "gas_mixture": {"type": "string"},
                                            "lxcat_db": {"type": "string"},
                                            "source_note": {"type": "string"},
                                            "status": {"type": "string"},
                                            "created_at": {"type": "string"},
                                            "reaction_count": {"type": "integer"},
                                            "verified_count": {"type": "integer"},
                                            "unverified_count": {"type": "integer"},
                                            "export_ready": {"type": "boolean"},
                                            "reactions": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "id",
                                                        "reaction_set_id",
                                                        "reaction",
                                                        "reactants",
                                                        "products",
                                                        "reaction_type",
                                                        "rate_type",
                                                        "rate_value",
                                                        "threshold_ev",
                                                        "cross_section_url",
                                                        "source_section_id",
                                                        "source_section_title",
                                                        "source_section_type",
                                                        "source_section_seq",
                                                        "source_label",
                                                        "confidence",
                                                        "verified",
                                                        "audit_log",
                                                    ],
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "reaction_set_id": {"type": "integer"},
                                                        "reaction": {"type": "string"},
                                                        "reactants": {"type": "array"},
                                                        "products": {"type": "array"},
                                                        "reaction_type": {"type": "string"},
                                                        "rate_type": {"type": "string"},
                                                        "rate_value": {"type": "string"},
                                                        "threshold_ev": {"type": "number"},
                                                        "cross_section_url": {"type": "string"},
                                                        "source_section_id": {"type": "integer"},
                                                        "source_section_title": {"type": "string"},
                                                        "source_section_type": {"type": "string"},
                                                        "source_section_seq": {"type": "integer"},
                                                        "source_label": {"type": "string"},
                                                        "confidence": {"type": "number"},
                                                        "verified": {"type": "boolean"},
                                                        "audit_log": {"type": "array"},
                                                    },
                                                },
                                            },
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.reaction_set_detail_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/reaction-sets/{} reaction fields missing: source_excerpt"]


def test_api_contract_validator_reports_missing_reaction_verify_response_field():
    validate_api_contract = load_validate_api_contract()
    response_fields = [
        field for field in validate_api_contract.REACTION_SET_DETAIL_RESPONSE_FIELDS if field != "export_ready"
    ]
    openapi = {
        "paths": {
            "/api/v1/reactions/{reaction_id}/verify": {
                "put": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": response_fields,
                                        "properties": {field: {"type": "string"} for field in response_fields},
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.reaction_verify_response_contract_issues(openapi=openapi)

    assert issues == ["PUT /api/v1/reactions/{}/verify missing response fields: export_ready"]


def test_api_contract_rag_query_response_exposes_cited_sources():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.rag_response_contract_issues()

    assert issues == []


def test_api_contract_system_status_response_exposes_release_readiness():
    validate_api_contract = load_validate_api_contract()

    issues = validate_api_contract.system_status_response_contract_issues()

    assert issues == []


def test_api_contract_validator_reports_missing_system_status_top_level_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/system/status": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "database_path",
                                            "runtime",
                                            "config_warnings",
                                            "storage",
                                            "storage_health",
                                            "external_capabilities",
                                            "status_counts",
                                            "counts",
                                            "demo_data",
                                        ],
                                        "properties": {
                                            "database_path": {"type": "string"},
                                            "runtime": {"type": "object"},
                                            "config_warnings": {"type": "array"},
                                            "storage": {"type": "object"},
                                            "storage_health": {"type": "object"},
                                            "external_capabilities": {"type": "object"},
                                            "status_counts": {"type": "object"},
                                            "counts": {"type": "object"},
                                            "demo_data": {"type": "object"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.system_status_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/system/status missing response fields: release_readiness"]


def test_api_contract_validator_reports_missing_system_status_nested_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/system/status": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "database_path",
                                            "runtime",
                                            "config_warnings",
                                            "storage",
                                            "storage_health",
                                            "external_capabilities",
                                            "status_counts",
                                            "counts",
                                            "demo_data",
                                            "release_readiness",
                                        ],
                                        "properties": {
                                            "database_path": {"type": "string"},
                                            "runtime": {
                                                "type": "object",
                                                "required": ["api_prefix", "scheduler_enabled", "scheduler_jobs"],
                                                "properties": {
                                                    "api_prefix": {"type": "string"},
                                                    "scheduler_enabled": {"type": "boolean"},
                                                    "scheduler_jobs": {"type": "array"},
                                                },
                                            },
                                            "config_warnings": {"type": "array"},
                                            "storage": {"type": "object"},
                                            "storage_health": {"type": "object"},
                                            "external_capabilities": {"type": "object"},
                                            "status_counts": {"type": "object"},
                                            "counts": {"type": "object"},
                                            "demo_data": {"type": "object"},
                                            "release_readiness": {"type": "object"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.system_status_response_contract_issues(openapi=openapi)

    assert issues == ["GET /api/v1/system/status runtime missing fields: version"]


def test_api_contract_validator_reports_missing_rag_response_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/rag/query": {
                "post": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["answer"],
                                        "properties": {
                                            "answer": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.rag_response_contract_issues(openapi=openapi)

    assert issues == ["POST /api/v1/rag/query missing response fields: sources"]


def test_api_contract_validator_reports_missing_rag_source_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/rag/query": {
                "post": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["answer", "sources"],
                                        "properties": {
                                            "answer": {"type": "string"},
                                            "sources": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": [
                                                        "document_id",
                                                        "paper_id",
                                                        "paper_title",
                                                        "section_id",
                                                        "section_seq",
                                                        "section_title",
                                                        "section_type",
                                                        "chunk_id",
                                                        "vector_id",
                                                        "score",
                                                    ],
                                                    "properties": {
                                                        "document_id": {"type": "integer"},
                                                        "paper_id": {"type": "integer"},
                                                        "paper_title": {"type": "string"},
                                                        "section_id": {"type": "integer"},
                                                        "section_seq": {"type": "integer"},
                                                        "section_title": {"type": "string"},
                                                        "section_type": {"type": "string"},
                                                        "chunk_id": {"type": "integer"},
                                                        "vector_id": {"type": "string"},
                                                        "score": {"type": "number"},
                                                    },
                                                },
                                            },
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.rag_response_contract_issues(openapi=openapi)

    assert issues == ["POST /api/v1/rag/query missing source fields: source_excerpt"]


def test_api_contract_validator_reports_missing_export_response_field():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/reaction-sets/{reaction_set_id}/export": {
                "post": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["reaction_set_id", "format"],
                                        "properties": {
                                            "reaction_set_id": {"type": "integer"},
                                            "format": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    issues = validate_api_contract.export_response_contract_issues(openapi=openapi)

    assert issues == [
        "POST /api/v1/reaction-sets/{}/export missing response fields: "
        "output_path, mime_type, reaction_count, audit_entry_count"
    ]


def test_api_contract_validator_reports_missing_semantic_error_status():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "paths": {
            "/api/v1/reaction-sets/{reaction_set_id}/export": {
                "post": {
                    "responses": {
                        "200": {"description": "OK"},
                        "422": {"description": "Validation Error"},
                    }
                }
            }
        }
    }

    issues = validate_api_contract.semantic_error_status_contract_issues(openapi=openapi)

    assert issues == ["POST /api/v1/reaction-sets/{}/export missing error responses: 400, 409"]


def test_api_contract_validator_reports_default_fastapi_validation_error_schema():
    validate_api_contract = load_validate_api_contract()
    openapi = {
        "components": {
            "schemas": {
                "HTTPValidationError": {"type": "object", "properties": {"detail": {"type": "array"}}}
            }
        },
        "paths": {
            "/api/v1/things": {
                "post": {
                    "responses": {
                        "422": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
                                }
                            }
                        }
                    }
                }
            }
        },
    }

    issues = validate_api_contract.error_response_contract_issues(openapi=openapi)

    assert issues == ["POST /api/v1/things 422 response must use unified error schema"]


def test_api_contract_validator_reports_missing_accepted_response_on_async_route(tmp_path):
    validate_api_contract = load_validate_api_contract()
    contract_path = tmp_path / "接口设计文档.md"
    contract_path.write_text("| POST | `/documents/{id}/parse` | 触发 GROBID 解析 |\n", encoding="utf-8")
    openapi_paths = {
        "/api/v1/documents/{document_id}/parse": {
            "post": {
                "responses": {
                    "200": {"description": "OK"},
                    "422": {"description": "Validation Error"},
                }
            }
        }
    }

    issues = validate_api_contract.async_response_contract_issues(contract_path, openapi_paths=openapi_paths)

    assert issues == ["POST /api/v1/documents/{id}/parse missing 202 response"]


def test_streamlit_requests_full_category_page_for_manual_selection():
    repo = Path(__file__).resolve().parent.parent
    streamlit_source = (repo / "streamlit_app.py").read_text(encoding="utf-8")

    assert 'api_get("/categories", page=1, page_size=100)' in streamlit_source


def test_schema_validator_accepts_schema_truth_source():
    validate_schema = load_validate_schema()
    repo = Path(__file__).resolve().parent.parent

    issues = validate_schema.validate_schema(repo / "docs" / "schema.sql")

    assert issues == []


def test_schema_validator_accepts_runtime_migrations():
    validate_schema = load_validate_schema()

    issues = validate_schema.validate_migrations()

    assert issues == []


def test_schema_validator_reports_missing_required_table(tmp_path):
    validate_schema = load_validate_schema()
    schema_path = tmp_path / "schema.sql"
    schema_path.write_text("PRAGMA foreign_keys = ON;\nCREATE TABLE journals (id INTEGER PRIMARY KEY);\n", encoding="utf-8")

    issues = validate_schema.validate_schema(schema_path)

    assert "missing table: papers" in issues
    assert "missing table: documents" in issues


def test_schema_validator_reports_missing_required_reaction_column(tmp_path):
    validate_schema = load_validate_schema()
    repo = Path(__file__).resolve().parent.parent
    schema_path = tmp_path / "schema.sql"
    schema_text = (repo / "docs" / "schema.sql").read_text(encoding="utf-8")
    schema_path.write_text(
        schema_text.replace(
            "    source_label      TEXT,                       -- 表号/出处标签，如 table 7: Reaction kinetics\n",
            "",
        ),
        encoding="utf-8",
    )

    issues = validate_schema.validate_schema(schema_path)

    assert "missing column: reactions.source_label" in issues


def test_schema_validator_reports_missing_required_workflow_columns(tmp_path):
    validate_schema = load_validate_schema()
    repo = Path(__file__).resolve().parent.parent
    schema_path = tmp_path / "schema.sql"
    schema_text = (repo / "docs" / "schema.sql").read_text(encoding="utf-8")
    schema_path.write_text(
        schema_text.replace(
            "    chemistry_status TEXT DEFAULT 'not_extracted', -- not_extracted/extracting/extracted/rejected/failed\n",
            "",
        ).replace(
            "    verified_at   TEXT,\n",
            "",
        ),
        encoding="utf-8",
    )

    issues = validate_schema.validate_schema(schema_path)

    assert "missing column: documents.chemistry_status" in issues
    assert "missing column: reaction_sets.verified_at" in issues


def test_schema_validator_reports_missing_required_search_columns(tmp_path):
    validate_schema = load_validate_schema()
    repo = Path(__file__).resolve().parent.parent
    schema_path = tmp_path / "schema.sql"
    schema_text = (repo / "docs" / "schema.sql").read_text(encoding="utf-8")
    schema_path.write_text(
        schema_text.replace(
            "    dedupe_key      TEXT UNIQUE,                -- 无 DOI 时的保守去重键，NULL 表示不自动合并\n",
            "",
        ).replace(
            "    papers_filtered INTEGER DEFAULT 0,\n",
            "",
        ),
        encoding="utf-8",
    )

    issues = validate_schema.validate_schema(schema_path)

    assert "missing column: papers.dedupe_key" in issues
    assert "missing column: crawl_jobs.papers_filtered" in issues


def test_schema_validator_runs_as_release_script():
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent

    result = subprocess.run(
        [sys.executable, "scripts/validate_schema.py"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_requirements_validator_accepts_declared_direct_dependencies():
    validate_requirements = load_validate_requirements()
    repo = Path(__file__).resolve().parent.parent

    missing = validate_requirements.missing_required_packages(repo / "requirements.txt")

    assert missing == []


def test_requirements_validator_reports_missing_direct_dependency(tmp_path):
    validate_requirements = load_validate_requirements()
    repo = Path(__file__).resolve().parent.parent
    requirements_path = tmp_path / "requirements.txt"
    requirements_text = (repo / "requirements.txt").read_text(encoding="utf-8")
    requirements_path.write_text(
        requirements_text.replace("requests==2.32.3\n", ""),
        encoding="utf-8",
    )

    missing = validate_requirements.missing_required_packages(requirements_path)

    assert missing == ["requests"]


def test_requirements_validator_rejects_unpinned_packages(tmp_path):
    validate_requirements = load_validate_requirements()
    requirements_path = tmp_path / "requirements.txt"
    requirements_path.write_text("fastapi==0.115.6\nrequests>=2.32\nstreamlit\n", encoding="utf-8")

    unpinned = validate_requirements.unpinned_packages(requirements_path)

    assert unpinned == ["requests", "streamlit"]


def test_requirements_validator_rejects_duplicate_packages(tmp_path):
    validate_requirements = load_validate_requirements()
    requirements_path = tmp_path / "requirements.txt"
    requirements_path.write_text("requests==2.32.3\nRequests==2.32.3\nhttpx==0.28.1\n", encoding="utf-8")

    duplicates = validate_requirements.duplicate_packages(requirements_path)

    assert duplicates == ["requests"]


def test_requirements_validator_reports_imported_package_missing_from_requirements(tmp_path):
    validate_requirements = load_validate_requirements()
    source_dir = tmp_path / "app"
    source_dir.mkdir()
    (source_dir / "uses_bs4.py").write_text("import bs4\nfrom pathlib import Path\n", encoding="utf-8")
    requirements_path = tmp_path / "requirements.txt"
    requirements_path.write_text("requests==2.32.3\n", encoding="utf-8")

    missing = validate_requirements.missing_imported_packages(requirements_path, [source_dir])

    assert missing == ["beautifulsoup4"]


def test_requirements_validator_ignores_standard_library_imports(tmp_path):
    validate_requirements = load_validate_requirements()
    source_dir = tmp_path / "scripts"
    source_dir.mkdir()
    (source_dir / "uses_stdlib.py").write_text(
        "import email.utils\nimport fnmatch\nimport importlib.util\nimport shlex\nimport subprocess\nimport zipfile\n",
        encoding="utf-8",
    )
    requirements_path = tmp_path / "requirements.txt"
    requirements_path.write_text("", encoding="utf-8")

    missing = validate_requirements.missing_imported_packages(requirements_path, [source_dir])

    assert missing == []


def test_requirements_validator_runs_as_release_script():
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent

    result = subprocess.run(
        [sys.executable, "scripts/validate_requirements.py"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_docs_links_validator_accepts_current_docs():
    validate_docs_links = load_validate_docs_links()
    repo = Path(__file__).resolve().parent.parent

    issues = validate_docs_links.broken_doc_links(repo)

    assert issues == []


def test_docs_links_validator_reports_missing_markdown_link(tmp_path):
    validate_docs_links = load_validate_docs_links()
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (tmp_path / "README.md").write_text("[Missing](docs/missing.md)\n", encoding="utf-8")

    issues = validate_docs_links.broken_doc_links(tmp_path)

    assert issues == ["README.md: missing link target docs/missing.md"]


def test_docs_links_validator_reports_missing_markdown_anchor(tmp_path):
    validate_docs_links = load_validate_docs_links()
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (tmp_path / "README.md").write_text("[Guide](docs/guide.md#missing-section)\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text("# Existing Section\n", encoding="utf-8")

    issues = validate_docs_links.broken_doc_links(tmp_path)

    assert issues == ["README.md: missing anchor target docs/guide.md#missing-section"]


def test_docs_links_validator_ignores_external_markdown_anchors(tmp_path):
    validate_docs_links = load_validate_docs_links()

    (tmp_path / "README.md").write_text("[External](https://example.test/docs#section)\n", encoding="utf-8")

    assert validate_docs_links.broken_doc_links(tmp_path) == []


def test_docs_links_validator_reports_missing_backtick_reference(tmp_path):
    validate_docs_links = load_validate_docs_links()
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("See `missing.sql` before release.\n", encoding="utf-8")

    issues = validate_docs_links.broken_doc_links(tmp_path)

    assert issues == ["docs/guide.md: missing reference target missing.sql"]


def test_docs_links_validator_reports_missing_backtick_runtime_file_reference(tmp_path):
    validate_docs_links = load_validate_docs_links()
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "Run `scripts/missing.py`, check `.github/workflows/missing.yml`, then copy `.env.example`.\n",
        encoding="utf-8",
    )

    issues = validate_docs_links.broken_doc_links(tmp_path)

    assert issues == [
        "docs/guide.md: missing reference target scripts/missing.py",
        "docs/guide.md: missing reference target .github/workflows/missing.yml",
        "docs/guide.md: missing reference target .env.example",
    ]


def test_docs_links_validator_ignores_backtick_glob_patterns(tmp_path):
    validate_docs_links = load_validate_docs_links()
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "Runtime references include `scripts/*.py` and `.github/workflows/*.yml`.\n",
        encoding="utf-8",
    )

    issues = validate_docs_links.broken_doc_links(tmp_path)

    assert issues == []


def test_docs_links_validator_runs_as_release_script():
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent

    result = subprocess.run(
        [sys.executable, "scripts/validate_docs_links.py"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_readme_commands_validator_accepts_current_readme():
    validate_readme_commands = load_validate_readme_commands()
    repo = Path(__file__).resolve().parent.parent

    issues = validate_readme_commands.missing_command_targets(repo)

    assert issues == []


def test_readme_commands_validator_reports_missing_script_target(tmp_path):
    validate_readme_commands = load_validate_readme_commands()
    (tmp_path / "README.md").write_text(
        "```bash\npython scripts/missing.py\nbash scripts/missing.sh\n```\n",
        encoding="utf-8",
    )

    issues = validate_readme_commands.missing_command_targets(tmp_path)

    assert issues == [
        "README.md: command target missing: scripts/missing.py",
        "README.md: command target missing: scripts/missing.sh",
    ]


def test_readme_commands_validator_reports_missing_scripts_module(tmp_path):
    validate_readme_commands = load_validate_readme_commands()
    (tmp_path / "README.md").write_text("```bash\npython -m scripts.missing_check\n```\n", encoding="utf-8")

    issues = validate_readme_commands.missing_command_targets(tmp_path)

    assert issues == ["README.md: command target missing: scripts/missing_check.py"]


def test_readme_commands_validator_checks_release_checklist_commands(tmp_path):
    validate_readme_commands = load_validate_readme_commands()
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (tmp_path / "README.md").write_text("# Test\n", encoding="utf-8")
    (docs_dir / "release-checklist.md").write_text(
        "```bash\npython scripts/missing_release_gate.py\n```\n",
        encoding="utf-8",
    )

    issues = validate_readme_commands.missing_command_targets(tmp_path)

    assert issues == [
        "docs/release-checklist.md: command target missing: scripts/missing_release_gate.py"
    ]


def test_readme_commands_validator_reports_unknown_python_script_option(tmp_path):
    validate_readme_commands = load_validate_readme_commands()
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "tool.py").write_text(
        "import argparse\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--known', action='store_true')\n"
        "parser.parse_args()\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("```bash\npython scripts/tool.py --known --missing\n```\n", encoding="utf-8")

    issues = validate_readme_commands.missing_command_targets(tmp_path)

    assert issues == ["README.md: option --missing not found in scripts/tool.py --help"]


def test_readme_commands_validator_reports_missing_local_curl_route(tmp_path):
    validate_readme_commands = load_validate_readme_commands()
    (tmp_path / "README.md").write_text(
        "```bash\ncurl 'http://127.0.0.1:8000/api/v1/not-a-real-route?debug=true'\n```\n",
        encoding="utf-8",
    )

    issues = validate_readme_commands.missing_command_targets(tmp_path)

    assert issues == ["README.md: curl route missing: GET /api/v1/not-a-real-route"]


def test_readme_commands_validator_reports_missing_uvicorn_app_target(tmp_path):
    validate_readme_commands = load_validate_readme_commands()
    (tmp_path / "README.md").write_text(
        "```bash\npython -m uvicorn app.missing:app --reload --host 127.0.0.1 --port 8000\n```\n",
        encoding="utf-8",
    )

    issues = validate_readme_commands.missing_command_targets(tmp_path)

    assert issues == ["README.md: uvicorn target missing: app.missing:app"]


def test_readme_commands_validator_reports_uvicorn_target_after_options(tmp_path):
    validate_readme_commands = load_validate_readme_commands()
    (tmp_path / "README.md").write_text(
        "```bash\nuvicorn --host 127.0.0.1 --port 8000 app.missing:app\n```\n",
        encoding="utf-8",
    )

    issues = validate_readme_commands.missing_command_targets(tmp_path)

    assert issues == ["README.md: uvicorn target missing: app.missing:app"]


def test_readme_commands_validator_runs_as_release_script():
    import subprocess
    import sys

    repo = Path(__file__).resolve().parent.parent

    result = subprocess.run(
        [sys.executable, "scripts/validate_readme_commands.py"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_env_loader_strips_inline_comments_without_touching_quoted_hashes(tmp_path):
    import subprocess

    repo = Path(__file__).resolve().parent.parent
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "API_PORT=8001 # local override",
                'LLM_API_KEY="sk-test#not-comment" # inline comment',
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "bash",
            "-lc",
            'source scripts/env.sh; load_env_file_if_unset "$1"; printf "%s\\n%s\\n" "$API_PORT" "$LLM_API_KEY"',
            "bash",
            str(env_file),
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["8001", "sk-test#not-comment"]
