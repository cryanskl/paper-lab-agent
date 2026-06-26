# Streamlit system status API errors were not surfaced

## 现象

- 触发页面：Streamlit 首屏 sidebar 初始化。
- 实际结果：`api_get("/system/status")` 或点击“检查 GROBID”后的 `api_get("/system/status", check_external=True)` 如果返回 API 错误，会抛出 `FrontendApiError`，sidebar 没有展示统一错误文本和原始 payload。
- 期望结果：页面显示 `format_error_payload(exc.payload, exc.status_code)`，同时展示 `exc.payload`，并停止继续渲染依赖 `status` 的指标。

## 原因

- 根因：sidebar 直接调用 `/system/status`，没有 `FrontendApiError` 专用处理分支。
- 影响范围：发布演示、新机器启动、外部健康检查排障；`/health` 成功但 `/system/status` 失败时，用户缺少结构化错误信息。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：sidebar 的系统状态读取和 GROBID live check 现在捕获 `FrontendApiError`，显示格式化错误和原始 payload，然后 `st.stop()`，避免后续 `status[...]` 访问产生二次错误。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_system_status_error_shows_payload_details -q` 修复前失败，提示缺少 `except FrontendApiError as exc:`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_system_status_error_shows_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k "streamlit_sidebar" -q` 通过，`11 passed, 357 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`686 passed`。
