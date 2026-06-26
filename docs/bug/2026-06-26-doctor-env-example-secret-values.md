# Doctor 预检未阻止 .env.example 示例密钥值

## 现象

`scripts/validate_env_example.py` 会要求 `OPENALEX_MAILTO`、`UNPAYWALL_EMAIL` 和 `LLM_API_KEY` 在 `.env.example` 中保持空值，避免把真实或示例 secret 写进可发布文件。但 `scripts/doctor.py` 的 Quick Start 预检只检查 key 是否存在，不检查这些 secret-like key 是否被填值。

## 原因

doctor 只解析 `.env.example` 的 key 集合，没有解析 value，也没有复用 secret hygiene 的发布规则。

## 修复

新增 `SECRET_LIKE_ENV_EXAMPLE_KEYS` 和 `env_example_values`。`check_env_example` 现在会在 key 存在检查之后，对 `OPENALEX_MAILTO`、`UNPAYWALL_EMAIL`、`LLM_API_KEY` 的非空值返回 `non_empty_env_example_secret`。

## 验证

先新增契约测试并确认红灯，再实现 doctor 的 secret-like value 检查。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_secret_like_values -q` 失败，doctor 未报告 `LLM_API_KEY=sk-test`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_secret_like_values -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -k doctor -q` 通过，`10 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`712 passed`。
