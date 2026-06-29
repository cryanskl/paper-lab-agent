# Streamlit document selectors accepted malformed document ids

## 现象

- 触发命令、接口或页面：Streamlit 文档页、RAG 页和化学库页从 `/api/v1/documents` 读取当前页文档后，用 `filter_documents_by_status()` 生成 selectbox 或 multiselect 的可选项。
- 实际结果：`filter_documents_by_status()` 只过滤非对象条目；缺少 `id`、字符串 `id` 或 bool `id` 的 document dict 仍会进入 UI 选择器。后续页面直接读取 `selected["id"]` 或 `int(document["id"])`，会触发 `KeyError`、`ValueError` 或把 bool 误当作整数。
- 期望结果：进入文档选择器的 document 必须带有非 bool 整数 `id`；异常条目被跳过，页面仍可稳定展示空态或有效文档。

## 原因

- 根因：文档选择器复用的筛选 helper 没有定义可选 document 的最低结构要求，只检查了 `isinstance(document, dict)`。
- 影响范围：文档详情加载、RAG 限定文档、化学库反应集加载，以及异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`filter_documents_by_status()` 现在只返回 dict 且 `id` 为非 bool 整数的 document；既有文档页、RAG 页和化学库页因为已统一使用该 helper，会自动获得相同保护。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_filter_documents_by_status_skips_documents_without_valid_id -q` 失败，缺 `id`、字符串 `id` 和 bool `id` 的 document 都进入了 `全部` 筛选结果。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_filter_documents_by_status_skips_documents_without_valid_id tests/test_frontend_api.py::test_filter_documents_by_status_skips_malformed_documents tests/test_frontend_api.py::test_filter_documents_by_status_matches_selected_workflow_state tests/test_frontend_api.py::test_document_option_label_surfaces_processing_states tests/test_frontend_api.py::test_document_option_label_handles_malformed_document -q` 通过，`5 passed`。
- Streamlit 契约：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_documents_tab_filters_current_page_by_status tests/test_api.py::test_streamlit_document_detail_errors_show_payload_details tests/test_api.py::test_streamlit_rag_tab_can_select_documents_for_query_scope tests/test_api.py::test_streamlit_rag_tab_filters_current_page_by_document_status tests/test_api.py::test_streamlit_chemistry_tab_can_select_document_for_reaction_sets tests/test_api.py::test_streamlit_chemistry_tab_filters_current_page_by_document_status -q` 通过，`6 passed`。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，`1203 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1203 passed`。
