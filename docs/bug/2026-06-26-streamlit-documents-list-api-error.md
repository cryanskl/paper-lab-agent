# Streamlit documents list API errors were not surfaced

## 现象

- 触发页面：Streamlit 文档 tab 初始化。
- 实际结果：`api_get("/documents", page=..., page_size=...)` 如果返回 API 错误，会抛出 `FrontendApiError`，文档页没有展示统一错误文本和原始 payload。
- 期望结果：页面显示 `format_error_payload(exc.payload, exc.status_code)`，同时展示 `exc.payload`，并停止继续渲染依赖 `documents_response` 的文档选择、解析、翻译、索引和抽取控件。

## 原因

- 根因：文档 tab 直接加载文档列表，没有 `FrontendApiError` 专用处理分支。
- 影响范围：PDF 导入后的文档列表、章节浏览、翻译预览、索引状态、化学抽取入口，以及新机器演示时的 API 排障。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：文档 tab 的文档列表加载现在捕获 `FrontendApiError`，显示格式化错误和原始 payload，然后 `st.stop()`，避免后续控件访问未定义的文档列表数据。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_documents_list_errors_show_payload_details -q` 修复前失败，提示缺少 `except FrontendApiError as exc:`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_documents_list_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k "streamlit_document or streamlit_documents" -q` 通过，`15 passed, 356 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`689 passed`。
