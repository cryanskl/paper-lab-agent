# Streamlit search filter metadata API errors were not surfaced

## 现象

- 触发页面：Streamlit 检索 tab 初始化。
- 实际结果：`api_get("/journals", active=True, page_size=100)` 或 `api_get("/categories")` 如果返回 API 错误，会抛出 `FrontendApiError`，检索页没有展示统一错误文本和原始 payload。
- 期望结果：页面显示 `format_error_payload(exc.payload, exc.status_code)`，同时展示 `exc.payload`，并停止继续渲染依赖 `journals` / `categories` 的筛选控件。

## 原因

- 根因：检索 tab 直接加载期刊和分类筛选元数据，没有 `FrontendApiError` 专用处理分支。
- 影响范围：P1 检索页初始化、白名单期刊筛选、分类筛选，以及新机器演示时的 API 排障。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：检索 tab 的期刊和分类元数据加载现在捕获 `FrontendApiError`，显示格式化错误和原始 payload，然后 `st.stop()`，避免后续控件访问未定义的筛选数据。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_search_filter_metadata_errors_show_payload_details -q` 修复前失败，提示缺少结构化错误展示。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_search_filter_metadata_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k "streamlit_search or streamlit_crawl" -q` 通过，`14 passed, 355 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`687 passed`。
