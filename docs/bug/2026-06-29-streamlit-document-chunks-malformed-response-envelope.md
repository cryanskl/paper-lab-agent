# Streamlit document chunks crashed on malformed response envelope

## 现象

- 触发命令、接口或页面：Streamlit 文档页加载 `/documents/{id}/chunks` 后渲染索引状态、chunks 分页信息和 chunk 预览。
- 实际结果：当 `/documents/{id}/chunks` 返回 2xx JSON 对象但缺少 `items`、`total`、`page`、`page_size`、`indexed` 或状态字段类型异常时，文档页会在直接索引 `chunks["indexed"]`、`chunks["total"]`、`chunks["items"]` 或分页字段时崩溃。
- 期望结果：文档页在读取 chunks 列表和索引状态字段前先规范化响应；异常 envelope 显示为空 chunks 列表和安全的索引状态，不影响文档详情页继续渲染。

## 原因

- 根因：文档页 chunks 列表直接读取 `/documents/{id}/chunks` 的分页字段和索引状态字段。通用分页 envelope helper 不能保留 `indexed`、`index_status`、`index_error`，因此该接口需要专门的响应状态规范化。
- 影响范围：索引状态展示、chunk 预览、文档状态表、发布演示中的异常 API 响应处理，以及代理层返回不完整 JSON 时的前端稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：新增 `document_chunks_response_state()`，规范化分页字段并补齐安全的 `indexed`、`index_status`、`index_error`；文档页在读取 chunks 字段前调用该 helper。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_document_chunks_response_state_normalizes_malformed_envelope tests/test_api.py::test_streamlit_document_chunks_normalizes_response_envelope -q` 失败，chunks 响应规范化 helper 与文档页调用均不存在。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_document_chunks_response_state_normalizes_malformed_envelope tests/test_api.py::test_streamlit_document_chunks_normalizes_response_envelope tests/test_api.py::test_streamlit_document_chunks_errors_show_payload_details tests/test_api.py::test_streamlit_documents_tab_preserves_api_index_status_values tests/test_api.py::test_streamlit_documents_tab_exposes_preview_and_index_status -q` 通过，5 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1238 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1238 passed。
