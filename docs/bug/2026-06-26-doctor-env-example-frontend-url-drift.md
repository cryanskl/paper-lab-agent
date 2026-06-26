# Doctor 预检未发现 FRONTEND_URL 运行时默认值漂移

## 现象

`.env.example` 中 `FRONTEND_URL` 应由 `STREAMLIT_HOST` 和 `STREAMLIT_PORT` 推导，例如 `STREAMLIT_PORT=9501` 时应为 `http://127.0.0.1:9501`。`scripts/validate_env_example.py` 能发现这种 runtime default drift，但 `scripts/doctor.py` 的 Quick Start 预检此前不会报告，导致前端入口文档和实际 Streamlit 端口可能不一致。

## 原因

doctor 只检查 `API_BASE_URL` 的 runtime 默认值漂移，没有覆盖 `FRONTEND_URL` 与 Streamlit host/port 的派生关系。

## 修复

新增 `frontend_url_runtime_issue`。`check_env_example` 现在会根据 `STREAMLIT_HOST`、`STREAMLIT_PORT` 推导期望的 `FRONTEND_URL`，不一致时返回 `env_example_runtime_default_drift`。

## 验证

先新增契约测试并确认红灯，再实现 doctor 的 `FRONTEND_URL` runtime drift 检查。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_frontend_url_runtime_drift -q` 失败，doctor 未报告 `STREAMLIT_PORT=9501` 后的 `FRONTEND_URL` 漂移。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_frontend_url_runtime_drift -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -k doctor -q` 通过，`13 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`715 passed`。
