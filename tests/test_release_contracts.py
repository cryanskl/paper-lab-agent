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


def test_gitignore_contains_required_release_hygiene_patterns():
    validate_release_hygiene = load_validate_release_hygiene()
    gitignore_path = Path(__file__).resolve().parent.parent / ".gitignore"

    missing = validate_release_hygiene.missing_required_gitignore_patterns(gitignore_path)

    assert missing == []


def test_release_hygiene_validator_reports_missing_gitignore_pattern(tmp_path):
    validate_release_hygiene = load_validate_release_hygiene()
    gitignore_path = tmp_path / ".gitignore"
    gitignore_path.write_text(".env\n.venv/\ndata/\n__pycache__/\n", encoding="utf-8")

    missing = validate_release_hygiene.missing_required_gitignore_patterns(gitignore_path)

    assert ".next/" in missing


def test_agents_truth_source_references_point_to_existing_files():
    repo = Path(__file__).resolve().parent.parent
    agents_path = repo / "AGENTS.md"
    agents_text = agents_path.read_text(encoding="utf-8")
    truth_source_names = {
        "PRD_等离子体文献系统.md",
        "schema.sql",
        "接口设计文档.md",
        "任务拆分_开发路线.md",
    }

    references = [
        reference
        for reference in re.findall(r"`([^`]+)`", agents_text)
        if Path(reference).name in truth_source_names
    ]
    missing = [reference for reference in references if not (repo / reference).exists()]

    assert references
    assert missing == []
