# Frontend document chunk selection crashed on malformed chunk options

## 现象

- 触发命令、接口或页面：Streamlit 文档页“索引”tab 使用 `st.selectbox(..., format_func=document_chunk_option_label)` 展示 chunk / vector 选项，并对选中项调用 `chunk_preview.get("text")` 预览内容；chunk 列表里混入非对象条目，或选中项的 `text` 不是字符串。
- 实际结果：`document_chunk_option_label()` 直接调用 `chunk.get()`，非对象 chunk 会触发 `AttributeError`；即使标签降级，选中异常 chunk 后直接 `.get("text")` 也会让页面崩溃。
- 期望结果：chunk 选择器应稳定降级：异常选项显示 `invalid · -`，异常或非文本预览显示为空字符串，页面继续展示 chunk 表和其它状态。

## 原因

- 根因：上一层 chunk 表格展示已做类型降级，但 selectbox 的标签函数和选中项预览仍假设 chunk 是 API 契约对象。
- 影响范围：Streamlit 文档页索引结果浏览、chunk/vector 定位、RAG 分块排障，以及接口契约漂移或历史脏数据下的演示稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：`document_chunk_option_label()` 对非对象 chunk 返回 `invalid · -`；新增 `document_chunk_preview_text()`，只在选中项为对象且 `text` 为字符串时返回文本；Streamlit 使用该 helper 渲染 `st.code()`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_chunk_option_label_handles_malformed_chunk tests/test_frontend_api.py::test_document_chunk_preview_text_handles_malformed_chunk_and_text -q` 失败，非对象 chunk 触发 `AttributeError: 'str' object has no attribute 'get'`，且缺少 `document_chunk_preview_text`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_documents_tab_exposes_preview_and_index_status -q` 失败，Streamlit 尚未使用 `document_chunk_preview_text(chunk_preview)`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_chunk_option_label_handles_malformed_chunk tests/test_frontend_api.py::test_document_chunk_preview_text_handles_malformed_chunk_and_text tests/test_frontend_api.py::test_document_chunk_option_label_uses_vector_and_section_title tests/test_frontend_api.py::test_document_chunk_option_label_falls_back_to_id_and_dash_title -q` 通过，`4 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_documents_tab_exposes_preview_and_index_status tests/test_api.py::test_streamlit_documents_tab_exposes_section_and_chunk_pagination_controls tests/test_api.py::test_streamlit_document_chunks_errors_show_payload_details -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`121 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1178 passed`。
