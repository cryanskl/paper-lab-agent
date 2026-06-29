# Streamlit document sections crashed on malformed response envelope

## 现象

- 触发命令、接口或页面：Streamlit 文档页加载 `/documents/{id}/sections` 后渲染章节预览、章节分页信息和章节表格。
- 实际结果：当 `/documents/{id}/sections` 返回 2xx JSON 对象但缺少 `items`、`total`、`page` 或 `page_size`，或这些字段类型异常时，文档页会在直接索引 `sections_response["items"]` 或分页字段时崩溃。
- 期望结果：文档页在读取章节列表字段前先规范化分页 envelope；异常 envelope 显示为空章节列表，不影响文档详情页继续渲染。

## 原因

- 根因：文档页章节列表直接读取 `/documents/{id}/sections` 的 `items`、`page`、`page_size` 和 `total` 字段，没有复用其他分页列表已使用的 `paginated_response_state()`。
- 影响范围：PDF 解析结果预览、翻译/索引状态复查入口、发布演示中的异常 API 响应处理，以及代理层返回不完整 JSON 时的前端稳定性。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：文档页在读取 `sections_response["items"]` 前调用 `paginated_response_state(sections_response, default_page_size=20)`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_document_sections_normalizes_response_envelope -q` 失败，文档页未规范化 sections 响应 envelope。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_document_sections_normalizes_response_envelope tests/test_api.py::test_streamlit_documents_tab_exposes_section_and_chunk_pagination_controls tests/test_api.py::test_streamlit_document_sections_errors_show_payload_details tests/test_api.py::test_streamlit_document_chunks_errors_show_payload_details -q` 通过，4 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1236 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1236 passed。
