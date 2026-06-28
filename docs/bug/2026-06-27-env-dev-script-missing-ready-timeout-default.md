# Env validator skipped dev script without ready timeout default

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_env_example.py`，且仓库内 `scripts/dev.sh` 存在但不包含 `DEV_READY_TIMEOUT="${DEV_READY_TIMEOUT:-...}"` 默认值表达式。
- 实际结果：validator 将缺失 runtime 默认值当作无需校验，并返回 0。
- 期望结果：validator 应返回非零，并报告启动脚本缺少 `DEV_READY_TIMEOUT` 默认值，避免 `.env.example` 无法和真实启动脚本默认值对齐。

## 原因

- 根因：`dev_ready_timeout_default()` 在脚本中找不到默认值表达式时返回 `None`，`script_runtime_default_mismatches()` 只在 `expected_timeout` 和 `actual_timeout` 同时存在且不一致时才追加 mismatch。
- 影响范围：release gate 中的 `.env.example` 校验；启动脚本缺少 readiness timeout 默认值时，发布检查可能误判通过。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`
- 关键行为：`.env.example` 声明 `DEV_READY_TIMEOUT` 但 `scripts/dev.sh` 解析不到对应默认值时，`script_runtime_default_mismatches()` 返回 `DEV_READY_TIMEOUT default missing from ...` mismatch，CLI 通过既有 `env example runtime defaults drifted` 输出失败。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_reports_dev_script_without_ready_timeout_default -q` 失败，当前 validator 返回 0。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_reports_dev_script_without_ready_timeout_default -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example_validator"` 通过，`13 passed, 306 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`926 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `926 passed`。
