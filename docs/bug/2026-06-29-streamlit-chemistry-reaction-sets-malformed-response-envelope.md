# Streamlit chemistry reaction sets crashed on malformed response envelope

## 现象

- 触发命令、接口或页面：Streamlit 化学库页点击“加载文档反应集”后渲染 `/documents/{id}/reaction-sets` 的分页信息、表格和反应集选择器。
- 实际结果：当 `/documents/{id}/reaction-sets` 返回 2xx JSON 对象但缺少 `items`、`total`、`page` 或 `page_size`，或这些字段类型异常时，化学库页会在直接索引 `document_reaction_sets["page"]`、`["page_size"]` 或 `["total"]` 时崩溃。
- 期望结果：化学库页在读取文档反应集分页字段前先规范化分页 envelope；异常 envelope 显示为空反应集列表，不影响化学库复核页继续渲染。

## 原因

- 根因：化学库页从 `st.session_state["document_reaction_sets"]` 读取响应后，直接使用分页字段，没有复用其他分页列表已使用的 `paginated_response_state()`。
- 影响范围：文档反应集选择、化学库人工复核入口、发布演示中的异常 API 响应处理，以及代理层返回不完整 JSON 时的前端稳定性。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：化学库页在读取 `document_reaction_sets` 字段前调用 `paginated_response_state(document_reaction_sets, default_page_size=20)`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_document_reaction_sets_normalizes_response_envelope -q` 失败，化学库页未规范化文档反应集响应 envelope。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_document_reaction_sets_normalizes_response_envelope tests/test_api.py::test_streamlit_chemistry_tab_exposes_reaction_set_pagination_controls tests/test_api.py::test_streamlit_chemistry_document_reaction_sets_show_empty_state tests/test_api.py::test_streamlit_chemistry_tab_can_select_document_for_reaction_sets -q` 通过，4 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1239 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1239 passed。
