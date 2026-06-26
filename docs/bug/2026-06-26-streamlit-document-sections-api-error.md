# Streamlit document sections API errors were not surfaced

## 现象

- 触发页面：Streamlit Documents tab 的章节列表区域。
- 实际结果：`api_get(f"/documents/{selected['id']}/sections", ...)` 如果返回 API 错误，会抛出 `FrontendApiError`，页面没有展示统一错误文本和原始 payload。
- 期望结果：页面显示 `format_error_payload(exc.payload, exc.status_code)`，同时展示 `exc.payload`，并停止继续渲染依赖 `sections_response` 的章节预览和后续内容。

## 原因

- 根因：文档章节列表加载沿用了裸 `api_get`，没有 `FrontendApiError` 专用处理分支。
- 影响范围：章节预览、翻译预览入口、索引状态展示和文档解析结果排障。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：章节列表加载现在捕获 `FrontendApiError`，显示格式化错误和原始 payload，然后 `st.stop()`，避免后续控件访问未定义的章节数据。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_document_sections_errors_show_payload_details -q` 修复前失败，提示缺少 `except FrontendApiError as exc:`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_document_sections_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k "streamlit_documents or streamlit_document" -q` 通过，`17 passed, 360 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`695 passed`。
