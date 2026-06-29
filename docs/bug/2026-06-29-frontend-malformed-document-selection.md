# Frontend document selection crashed on malformed document items

## 现象

- 触发命令、接口或页面：Streamlit 文档页从 `/documents` 读取 `items` 后先调用 `filter_documents_by_status(docs, document_status_filter)`，再用 `st.selectbox("文档", display_docs, format_func=document_option_label)` 展示文档选项；文档列表里混入非对象条目。
- 实际结果：`filter_documents_by_status(..., "全部")` 会把非对象条目原样返回，后续 `document_option_label()` 在字符串上调用 `.get()` 触发 `AttributeError`；非“全部”筛选也会在 `document.get(field)` 处崩溃。
- 期望结果：文档选择入口应稳定降级：筛选阶段跳过非对象条目，label helper 对异常选项返回稳定占位，页面继续展示有效文档或空状态。

## 原因

- 根因：文档页已经把状态筛选和 label 逻辑抽到 helper，但 helper 仍假设 `/documents` 的 `items` 全部是 API 契约对象。
- 影响范围：Streamlit 文档页入口、PDF 解析/翻译/RAG/化学库工作流的文档选择，以及接口契约漂移或历史脏数据下的演示稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`filter_documents_by_status()` 先过滤非对象 document，再按状态筛选；`document_option_label()` 对非对象 document 返回 `#- · document · parse=unknown · index=unknown · chemistry=unknown`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_filter_documents_by_status_skips_malformed_documents tests/test_frontend_api.py::test_document_option_label_handles_malformed_document -q` 失败，`全部` 筛选返回字符串导致 `TypeError: string indices must be integers`，且 `document_option_label()` 触发 `AttributeError: 'str' object has no attribute 'get'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_filter_documents_by_status_skips_malformed_documents tests/test_frontend_api.py::test_document_option_label_handles_malformed_document tests/test_frontend_api.py::test_filter_documents_by_status_matches_selected_workflow_state tests/test_frontend_api.py::test_document_option_label_surfaces_processing_states tests/test_frontend_api.py::test_document_option_label_includes_linked_paper_identity tests/test_frontend_api.py::test_document_option_label_falls_back_to_file_name_and_unknown_states -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1184 passed`。
