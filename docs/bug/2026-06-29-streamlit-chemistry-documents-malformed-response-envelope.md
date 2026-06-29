# Streamlit chemistry documents crashed on malformed response envelope

## 现象

- 触发命令、接口或页面：Streamlit 化学库页完成 `/documents` 请求后渲染文档分页、状态筛选和“化学库文档”选择器。
- 实际结果：当 `/documents` 返回 2xx JSON 对象但缺少 `items`、`total`、`page` 或 `page_size`，或这些字段类型异常时，化学库页会在直接索引响应字段时崩溃。
- 期望结果：化学库文档选择区在渲染前复用文档响应 envelope 规范化逻辑；异常 envelope 显示为空文档列表，不影响化学库页继续渲染。

## 原因

- 根因：化学库文档选择区复用了 `/documents` 接口，但没有像文档页一样调用 `documents_response_state()`，仍直接读取 `chemistry_documents_response["items"]`、`["page"]`、`["page_size"]` 和 `["total"]`。
- 影响范围：化学库抽取/审核入口、发布演示中的异常 API 响应处理，以及历史/代理层返回不完整 JSON 时的前端稳定性。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：chemistry tab 在读取文档列表字段前调用 `documents_response_state()`，与文档页和 RAG tab 保持一致。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_tab_normalizes_document_response_envelope -q` 失败，chemistry tab 未规范化 `/documents` 响应 envelope。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_tab_normalizes_document_response_envelope tests/test_api.py::test_streamlit_chemistry_tab_exposes_document_pagination_controls tests/test_api.py::test_streamlit_chemistry_documents_list_errors_show_payload_details tests/test_api.py::test_streamlit_chemistry_tab_can_select_document_for_reaction_sets tests/test_api.py::test_streamlit_chemistry_tab_filters_current_page_by_document_status -q` 通过，5 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1230 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1230 passed。
