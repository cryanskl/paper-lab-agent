# Streamlit RAG query API errors did not show payload details

## 现象

- 触发页面：Streamlit 问答 tab 的“提问”按钮。
- 实际结果：`api_post("/rag/query", ...)` 返回 API 错误时，页面只显示 `format_error_payload(rag_payload, status)`，没有展示原始 payload。
- 期望结果：页面在显示格式化错误文本的同时展示 `rag_payload` JSON，便于定位 RAG 查询失败的错误码、message 和后端响应体。

## 原因

- 根因：RAG 查询失败分支只调用 `st.warning(...)`，遗漏了其他 Streamlit 错误路径已使用的 `st.json(...)`。
- 影响范围：问答演示、RAG 查询排障、文档证据链路调试。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：RAG 查询失败时现在同时展示格式化错误和原始 `rag_payload` payload。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_rag_query_errors_show_payload_details -q` 修复前失败，提示缺少 `st.json(rag_payload)`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_rag_query_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k streamlit_rag -q` 通过，`7 passed, 377 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`702 passed`。
