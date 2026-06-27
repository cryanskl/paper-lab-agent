# Doctor skipped missing dev script during env example check

## 现象

- 触发命令、接口或页面：直接调用 `check_env_example(repo)`，且仓库下不存在 `scripts/dev.sh`。
- 实际结果：doctor 跳过 `DEV_READY_TIMEOUT` runtime 默认值校验，并返回 `pass`。
- 期望结果：doctor 应报告缺失 `scripts/dev.sh`，避免 `.env.example` 中的 `DEV_READY_TIMEOUT` 无法和真实启动脚本默认值对齐。

## 原因

- 根因：`dev_ready_timeout_default()` 在 `scripts/dev.sh` 不存在时返回 `None`，`dev_ready_timeout_runtime_issue()` 将 `expected is None` 当作无需诊断。
- 影响范围：Quick Start 预检和 release gate 中的 doctor 检查；直接调用 `check_env_example()` 时可能把缺少启动脚本的 checkout 误判为 `.env.example` 合格。

## 修复

- 修改文件：`scripts/doctor.py`、`tests/test_release_contracts.py`
- 关键行为：读取 dev script 默认值前，如果 `scripts/dev.sh` 不存在，返回 `dev_script_missing` issue；其他 `.env.example` 测试 fixture 显式创建最小 `scripts/dev.sh`，保持测试关注点独立。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_reports_missing_dev_script -q` 失败，当前实现返回 `pass`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_reports_missing_dev_script -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "doctor_env_example"` 通过，`13 passed, 304 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`924 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `924 passed`。
