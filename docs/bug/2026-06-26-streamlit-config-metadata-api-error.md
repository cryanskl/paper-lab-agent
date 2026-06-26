# Streamlit config metadata API errors were not surfaced

## 现象

- 触发页面：Streamlit 配置 tab 初始化。
- 实际结果：`api_get("/journals", page=..., page_size=...)` 或 `api_get("/categories", page=1, page_size=100)` 如果返回 API 错误，会抛出 `FrontendApiError`，配置页没有展示统一错误文本和原始 payload。
- 期望结果：页面显示 `format_error_payload(exc.payload, exc.status_code)`，同时展示 `exc.payload`，并停止继续渲染依赖 `journals_response` / `categories_response` 的配置控件。

## 原因

- 根因：配置 tab 直接加载期刊和分类管理数据，没有 `FrontendApiError` 专用处理分支。
- 影响范围：期刊白名单管理、分类管理、新机器演示和 API 排障。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：配置 tab 的期刊和分类元数据加载现在捕获 `FrontendApiError`，显示格式化错误和原始 payload，然后 `st.stop()`，避免后续控件访问未定义的管理数据。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_metadata_errors_show_payload_details -q` 修复前失败，提示缺少 `except FrontendApiError as exc:`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_metadata_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k "streamlit_config" -q` 通过，`8 passed, 362 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`688 passed`。
