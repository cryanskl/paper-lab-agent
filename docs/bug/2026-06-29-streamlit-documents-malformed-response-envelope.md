# Streamlit documents page crashed on malformed response envelope

## 现象

- 触发命令、接口或页面：Streamlit 文档页完成 `/documents` 请求后渲染分页、总数、状态筛选和文档列表。
- 实际结果：当 `/documents` 返回 2xx JSON 对象但缺少 `items`、`total`、`page` 或 `page_size`，或这些字段类型异常时，页面会在直接索引响应字段时崩溃。
- 期望结果：文档页在渲染前把响应 envelope 规范成 `{items,total,page,page_size}`；异常 envelope 显示为空文档列表，不影响页面继续渲染。

## 原因

- 根因：文档页只过滤了单条 document item，没有在使用 `documents_response["items"]`、`["page"]`、`["page_size"]` 和 `["total"]` 前校验列表响应 envelope。
- 影响范围：文档页上传后的列表浏览、发布演示中的异常 API 响应处理，以及历史/代理层返回不完整 JSON 时的前端稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `documents_response_state()`，将异常响应规范为空文档列表；Streamlit 文档页在渲染分页、筛选和列表前统一调用该 helper。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_documents_response_state_handles_malformed_envelope tests/test_api.py::test_streamlit_documents_tab_normalizes_response_envelope -q` 失败，helper 缺失且文档页未规范化响应 envelope。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_documents_response_state_handles_malformed_envelope tests/test_api.py::test_streamlit_documents_tab_normalizes_response_envelope tests/test_api.py::test_streamlit_documents_tab_exposes_pagination_controls tests/test_api.py::test_streamlit_documents_list_errors_show_payload_details tests/test_api.py::test_streamlit_documents_tab_filters_current_page_by_status tests/test_api.py::test_streamlit_documents_tab_shows_empty_state -q` 通过，6 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1228 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1228 passed。
