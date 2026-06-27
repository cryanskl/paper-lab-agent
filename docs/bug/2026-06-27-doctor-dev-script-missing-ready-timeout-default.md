# Doctor skipped dev script without ready timeout default

## 现象

- 触发命令、接口或页面：直接调用 `check_env_example(repo)`，且 `scripts/dev.sh` 存在但不包含 `DEV_READY_TIMEOUT="${DEV_READY_TIMEOUT:-...}"` 默认值表达式。
- 实际结果：doctor 将缺失 runtime 默认值当作无需校验，并可能返回 `pass`。
- 期望结果：doctor 应报告启动脚本缺少 `DEV_READY_TIMEOUT` 默认值，避免 `.env.example` 无法和真实启动脚本默认值对齐。

## 原因

- 根因：`dev_ready_timeout_default()` 在脚本中找不到默认值表达式时返回 `None`，`dev_ready_timeout_runtime_issue()` 将 `expected is None` 当作无需诊断。
- 影响范围：Quick Start 预检和 release gate 中的 doctor 检查；直接调用 `check_env_example()` 时可能把缺失 runtime 默认值来源的启动脚本误判为合格。

## 修复

- 修改文件：`scripts/doctor.py`、`tests/test_release_contracts.py`
- 关键行为：`scripts/dev.sh` 可读但缺少 `DEV_READY_TIMEOUT="${DEV_READY_TIMEOUT:-...}"` 时返回 `dev_script_missing_ready_timeout_default` issue；只有找到默认值后才继续和 `.env.example` 比较。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_reports_dev_script_without_ready_timeout_default -q` 失败，当前实现返回 `pass`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_reports_dev_script_without_ready_timeout_default -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "doctor_env_example"` 通过，`14 passed, 304 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`925 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `925 passed`。
