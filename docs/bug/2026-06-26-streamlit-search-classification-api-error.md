# Streamlit search classification API errors did not show payload details

## 现象

- 触发页面：Streamlit 检索 tab 的搜索结果“触发分类”按钮。
- 实际结果：`api_post(f"/papers/{paper['id']}/classify")` 返回 API 错误时，页面只显示 `format_error_payload(classified_paper, status_code)`，没有展示原始 payload。
- 期望结果：页面在显示格式化错误文本的同时展示 `classified_paper` JSON，便于定位分类任务失败的错误码、message 和后端响应体。

## 原因

- 根因：分类失败分支只调用 `st.warning(...)`，遗漏了其他 Streamlit 错误路径已使用的 `st.json(...)`。
- 影响范围：搜索结果分类、分类 adapter 排障、检索页演示。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：搜索结果触发分类失败时现在同时展示格式化错误和原始 `classified_paper` payload。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_search_classification_errors_show_payload_details -q` 修复前失败，提示缺少 `st.json(classified_paper)`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_search_classification_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k "streamlit_search or streamlit_crawl" -q` 通过，`17 passed, 364 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`699 passed`。
