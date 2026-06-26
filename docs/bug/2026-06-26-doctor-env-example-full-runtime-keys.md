# Doctor 预检未覆盖完整 .env.example 运行配置

## 现象

`scripts/validate_env_example.py` 会检查 settings alias 和 `scripts/dev.sh` 运行时 URL 配置，例如 `PAPER_LAB_DATA_DIR`、`PAPER_LAB_PDF_DIR`、`API_BASE_URL`、`FRONTEND_URL` 和 `DEV_READY_TIMEOUT`。但 `scripts/doctor.py` 只检查外部依赖和少量存储键。新机器按 Quick Start 先运行 doctor 时，如果 `.env.example` 缺少这些运行配置，doctor 仍可能通过。

## 原因

doctor 的 `.env.example` 必需键列表停留在早期最小集合，没有跟随完整 env validator 的 `required_env_keys()` 范围扩展。

## 修复

扩展 `REQUIRED_ENV_EXAMPLE_KEYS`，覆盖外部依赖、settings alias、调度/学术 API 参数，以及 `scripts/dev.sh` 运行时 URL/端口配置。契约测试改为逐个删除 `validate_env_example.required_env_keys()` 返回的键，确认 doctor 对完整运行配置都能报 `missing_env_example_key`。

## 验证

先扩大契约测试并确认红灯，再补齐 doctor 的必需键列表。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_matches_required_runtime_keys -q` 失败，doctor 未报告缺失的 `PAPER_LAB_DATA_DIR`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_matches_required_runtime_keys -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -k doctor -q` 通过，`9 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`711 passed`。
