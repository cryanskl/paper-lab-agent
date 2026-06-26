# Streamlit document detail API errors were not surfaced

## 现象

- 触发页面：Streamlit Documents tab 的文档详情区域。
- 实际结果：`api_get(f"/documents/{selected['id']}")` 如果返回 API 错误，会抛出 `FrontendApiError`，页面没有展示统一错误文本和原始 payload。
- 期望结果：页面显示 `format_error_payload(exc.payload, exc.status_code)`，同时展示 `exc.payload`，并停止继续渲染依赖 `document_detail` 的下载、解析、索引、分段和翻译控件。

## 原因

- 根因：文档详情加载沿用了裸 `api_get`，没有 `FrontendApiError` 专用处理分支。
- 影响范围：文档详情、原文/TEI 下载、解析/索引/翻译演示和 API 排障。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：文档详情加载现在捕获 `FrontendApiError`，显示格式化错误和原始 payload，然后 `st.stop()`，避免后续控件访问未定义的详情数据。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_document_detail_errors_show_payload_details -q` 修复前失败，提示缺少 `except FrontendApiError as exc:`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_document_detail_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k "streamlit_documents or streamlit_document" -q` 通过，`16 passed, 360 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`694 passed`。
