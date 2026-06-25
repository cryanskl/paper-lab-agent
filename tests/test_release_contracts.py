import re
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
        "name: ci\non: [push, pull_request, workflow_dispatch]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    timeout-minutes: 15\n    steps:\n      - run: bash scripts/release_check.sh\n",
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
        "python scripts/health_check.py --require-release-ready",
        "python scripts/health_check.py --require-frontend",
        "python scripts/health_check.py --require-grobid",
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


def test_doctor_preflight_is_documented_and_in_release_gate():
    repo = Path(__file__).resolve().parent.parent
    readme = (repo / "README.md").read_text(encoding="utf-8")
    checklist = (repo / "docs" / "release-checklist.md").read_text(encoding="utf-8")
    release_check = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert "python scripts/doctor.py --compact" in readme
    assert "python scripts/doctor.py --strict --compact" in readme
    assert "python scripts/doctor.py --strict --compact" in checklist
    assert "scripts/doctor.py" in release_check
    assert "scripts/doctor.py --help" in release_check
    assert "scripts/doctor.py --strict --compact" in release_check


def test_release_check_compiles_application_package():
    repo = Path(__file__).resolve().parent.parent
    release_check = (repo / "scripts" / "release_check.sh").read_text(encoding="utf-8")

    assert "-m compileall" in release_check
    assert " app " in release_check or " app\n" in release_check


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

    assert '"document_list_total": 1' in release_text
    assert '"document_detail_parse_status": "uploaded"' in release_text
    assert '"document_detail_has_paper": True' in release_text
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
        "import email.utils\nimport fnmatch\nimport importlib.util\nimport shlex\nimport subprocess\n",
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
