# Streamlit document chunks API errors were not surfaced

## 现象

- 触发页面：Streamlit Documents tab 的索引 chunks 加载区域。
- 实际结果：`api_get(f"/documents/{selected['id']}/chunks", ...)` 如果返回 API 错误，会抛出 `FrontendApiError`，页面没有展示统一错误文本和原始 payload。
- 期望结果：页面显示 `format_error_payload(exc.payload, exc.status_code)`，同时展示 `exc.payload`，并停止继续渲染依赖 `chunks` 的索引状态、状态表和 chunks 预览。

## 原因

- 根因：文档 chunks 列表加载沿用了裸 `api_get`，没有 `FrontendApiError` 专用处理分支。
- 影响范围：索引状态展示、RAG chunk 证据预览、文档索引结果排障。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：chunks 列表加载现在捕获 `FrontendApiError`，显示格式化错误和原始 payload，然后 `st.stop()`，避免后续控件访问未定义的 chunks 数据。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_document_chunks_errors_show_payload_details -q` 修复前失败，提示缺少 `except FrontendApiError as exc:`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_document_chunks_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k "streamlit_documents or streamlit_document" -q` 通过，`18 passed, 360 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`696 passed`。
