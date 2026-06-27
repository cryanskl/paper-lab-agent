# Frontend API base URL whitespace produced invalid request URLs

## 现象

- 触发命令、接口或页面：Streamlit 前端或环境变量把 API base URL 传给 `request_json_status()`，且值带首尾空白，例如 `  http://api.test/api/v1/  `。
- 实际结果：前端适配层只移除尾部 `/`，没有清理空白，最终拼出的请求 URL 类似 `  http://api.test/api/v1/  /system/status`。
- 期望结果：base URL 应先移除首尾空白，再按已有规则去尾部斜杠并拼接路径。

## 原因

- 根因：`app/frontend_api.py` 的 `normalize_base_url()` 只调用 `rstrip("/")`，未处理来自配置或输入框的首尾空白。
- 影响范围：Streamlit 前端启动健康检查、系统状态、检索、导入和复核等所有经前端适配层发出的 API 请求。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`normalize_base_url()` 先 `strip()` 再移除尾部斜杠，保留已有路径标准化逻辑。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_frontend_api_status_request_strips_base_url_whitespace -q` 失败，请求 URL 实际为 `  http://api.test/api/v1/  /system/status`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_frontend_api_status_request_strips_base_url_whitespace -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`63 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`874 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `874 passed`。
