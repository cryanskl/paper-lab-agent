# Doctor 预检未发现 .env.example 默认值漂移

## 现象

`scripts/validate_env_example.py` 会检查 `.env.example` 中的 settings 默认值是否与 `app/config.py` 保持一致，例如 `LLM_MODEL=gpt-4o-mini`。但 `scripts/doctor.py` 作为 Quick Start 预检只检查 key 是否存在和 secret-like 值是否为空，无法发现 `LLM_MODEL=legacy-model` 这类默认值漂移。

## 原因

doctor 的 `.env.example` 检查没有维护默认值契约，导致新机器启动前预检与 release validator 覆盖范围不一致。

## 修复

新增 `ENV_EXAMPLE_DEFAULTS`、`normalize_env_value` 和 `env_values_match`。`check_env_example` 现在会对存储路径、GROBID URL、LLM/embedding 默认模型、scheduler 和学术 API 参数做默认值漂移检查，并允许 `./data` 与 `data`、`0` 与 `0.0` 这类等价写法。

## 验证

先新增契约测试并确认红灯，再实现 doctor 默认值漂移检查。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_settings_default_drift -q` 失败，doctor 未报告 `LLM_MODEL=legacy-model`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_settings_default_drift -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -k doctor -q` 通过，`11 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`713 passed`。
