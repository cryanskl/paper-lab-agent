# Streamlit chemistry documents list API errors were not surfaced

## 现象

- 触发页面：Streamlit 化学库 tab 初始化。
- 实际结果：`api_get("/documents", page=..., page_size=...)` 如果返回 API 错误，会抛出 `FrontendApiError`，化学库页没有展示统一错误文本和原始 payload。
- 期望结果：页面显示 `format_error_payload(exc.payload, exc.status_code)`，同时展示 `exc.payload`，并停止继续渲染依赖 `chemistry_documents_response` 的文档选择、反应集加载、复核和导出控件。

## 原因

- 根因：化学库 tab 直接加载可选文档列表，没有 `FrontendApiError` 专用处理分支。
- 影响范围：化学库文档选择、反应集复核、导出演示，以及新机器启动后的 API 排障。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：化学库 tab 的文档列表加载现在捕获 `FrontendApiError`，显示格式化错误和原始 payload，然后 `st.stop()`，避免后续控件访问未定义的文档列表数据。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_documents_list_errors_show_payload_details -q` 修复前失败，提示缺少结构化错误展示。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_documents_list_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k "streamlit_chemistry" -q` 通过，`15 passed, 358 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`691 passed`。
