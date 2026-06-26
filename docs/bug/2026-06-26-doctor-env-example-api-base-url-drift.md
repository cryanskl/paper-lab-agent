# Doctor 预检未发现 API_BASE_URL 运行时默认值漂移

## 现象

`.env.example` 中 `API_BASE_URL` 应由 `API_HOST` 和 `API_PORT` 推导，例如 `API_PORT=9000` 时应为 `http://127.0.0.1:9000/api/v1`。`scripts/validate_env_example.py` 能发现这种 runtime default drift，但 `scripts/doctor.py` 的 Quick Start 预检此前不会报告，导致新机器启动前可能拿到不一致的前端 API 地址。

## 原因

doctor 只检查静态默认值，没有按 `scripts/dev.sh`/runtime 规则推导 `API_BASE_URL`。

## 修复

新增 `connect_host`、`url_host` 和 `api_base_url_runtime_issue`。`check_env_example` 现在会根据 `API_HOST`、`API_PORT` 推导期望的 `API_BASE_URL`，不一致时返回 `env_example_runtime_default_drift`。

## 验证

先新增契约测试并确认红灯，再实现 doctor 的 `API_BASE_URL` runtime drift 检查。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_api_base_url_runtime_drift -q` 失败，doctor 未报告 `API_PORT=9000` 后的 `API_BASE_URL` 漂移。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_api_base_url_runtime_drift -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -k doctor -q` 通过，`12 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`714 passed`。
