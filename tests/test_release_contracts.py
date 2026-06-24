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


def test_env_example_contains_required_external_dependency_keys():
    validate_env_example = load_validate_env_example()
    env_path = Path(__file__).resolve().parent.parent / ".env.example"

    missing = validate_env_example.missing_required_keys(env_path)

    assert missing == []


def test_env_example_validator_reports_missing_required_key(tmp_path):
    validate_env_example = load_validate_env_example()
    env_path = tmp_path / ".env.example"
    env_path.write_text(
        "\n".join(
            [
                "OPENALEX_MAILTO=",
                "UNPAYWALL_EMAIL=",
                "GROBID_URL=http://127.0.0.1:8070",
                "LLM_API_KEY=",
                "EMBEDDING_MODEL=local-hash",
                "DATABASE_PATH=./data/plasma.db",
            ]
        ),
        encoding="utf-8",
    )

    missing = validate_env_example.missing_required_keys(env_path)

    assert missing == ["VECTOR_DB_PATH"]
