# Streamlit search resolve OA API errors did not show payload details

## 现象

- 触发页面：Streamlit 检索 tab 的搜索结果“重新解析 OA”按钮。
- 实际结果：`api_post(f"/papers/{paper['id']}/resolve-oa")` 返回 API 错误时，页面只显示 `format_error_payload(resolved_paper, status_code)`，没有展示原始 payload。
- 期望结果：页面在显示格式化错误文本的同时展示 `resolved_paper` JSON，便于定位 Unpaywall/OA 解析失败的错误码、message 和后端响应体。

## 原因

- 根因：OA 解析失败分支只调用 `st.warning(...)`，遗漏了其他 Streamlit 错误路径已使用的 `st.json(...)`。
- 影响范围：搜索结果 OA 解析、开放获取链接排障、检索页演示。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：搜索结果重新解析 OA 失败时现在同时展示格式化错误和原始 `resolved_paper` payload。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_search_resolve_oa_errors_show_payload_details -q` 修复前失败，提示缺少 `st.json(resolved_paper)`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_search_resolve_oa_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k "streamlit_search or streamlit_crawl" -q` 通过，`18 passed, 364 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`700 passed`。
