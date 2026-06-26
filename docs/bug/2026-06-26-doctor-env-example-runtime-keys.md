# Doctor 预检漏报部分 .env.example 必需键

## 现象

`scripts/doctor.py` 的 `.env.example` 预检只检查 `DATABASE_PATH`、`GROBID_URL`、`OPENALEX_MAILTO`、`UNPAYWALL_EMAIL` 和 `LLM_API_KEY`。如果新机器上的 `.env.example` 缺少 `EMBEDDING_MODEL` 或 `VECTOR_DB_PATH`，doctor 仍可能通过，导致启动前预检不能完整覆盖项目约定的最小运行配置。

## 原因

doctor 内部硬编码了一组较早期的 env key，没有与 `scripts/validate_env_example.py` 中的必需运行配置保持一致。

## 修复

在 `scripts/doctor.py` 中提取 `REQUIRED_ENV_EXAMPLE_KEYS` 常量，并补齐 `OPENALEX_MAILTO`、`UNPAYWALL_EMAIL`、`GROBID_URL`、`LLM_API_KEY`、`EMBEDDING_MODEL`、`VECTOR_DB_PATH` 和 `DATABASE_PATH`。新增契约测试逐个删除这些键，确认 doctor 会返回 `missing_env_example_key`。

## 验证

先新增契约测试并确认红灯，再补齐 doctor 的必需 env key 列表。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_matches_required_runtime_keys -q` 失败，`EMBEDDING_MODEL` 未被 doctor 报告。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_matches_required_runtime_keys -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -k doctor -q` 通过，`8 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`710 passed`。
