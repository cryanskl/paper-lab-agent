# Doctor 预检未发现 DEV_READY_TIMEOUT 运行时默认值漂移

## 现象

`.env.example` 中 `DEV_READY_TIMEOUT` 应与 `scripts/dev.sh` 的默认启动等待时间保持一致。`scripts/validate_env_example.py` 能发现 `DEV_READY_TIMEOUT=10` 与脚本默认 `30` 不一致，但 `scripts/doctor.py` 的 Quick Start 预检此前不会报告，导致新机器启动前可能使用错误的 readiness 等待时间。

## 原因

doctor 只检查 API/前端 URL 的 runtime 派生值，没有从 `scripts/dev.sh` 解析 `DEV_READY_TIMEOUT` 的实际默认值。

## 修复

新增 `dev_ready_timeout_default` 和 `dev_ready_timeout_runtime_issue`。`check_env_example` 现在会读取 `scripts/dev.sh` 中的 `DEV_READY_TIMEOUT="${DEV_READY_TIMEOUT:-...}"` 默认值，并在 `.env.example` 不一致时返回 `env_example_runtime_default_drift`。

## 验证

先新增契约测试并确认红灯，再实现 doctor 的 `DEV_READY_TIMEOUT` runtime drift 检查。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_dev_ready_timeout_runtime_drift -q` 失败，doctor 未报告 `DEV_READY_TIMEOUT=10` 与脚本默认 `30` 不一致。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_dev_ready_timeout_runtime_drift -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -k doctor -q` 通过，`14 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`716 passed`。
