# Frontend document chunk rows crashed on malformed chunk payloads

## 现象

- 触发命令、接口或页面：Streamlit 文档页“索引”tab 调用 `document_chunk_rows(chunks["items"])` 渲染 chunk / vector 列表；chunk 列表里混入非对象条目，或单条 chunk 的 `text` 不是字符串。
- 实际结果：`document_chunk_rows()` 直接调用 `chunk.get()`，非对象 chunk 触发 `AttributeError`；非字符串 `text` 会继续传入 `summarize_text()` 并在 `.split()` 上崩溃。
- 期望结果：chunk 表展示层应稳定降级：异常 chunk 显示为 `invalid` 行，异常文本显示 `text_preview=invalid` 且 `text_chars=0`，同一页里的有效 chunk 继续展示。

## 原因

- 根因：展示层 helper 假设 chunk 列表完全符合 API 契约，没有在 Streamlit 渲染边界校验 chunk 条目和 `text` 类型。
- 影响范围：Streamlit 文档页索引结果浏览、RAG 分块排障，以及接口契约漂移或历史脏数据下的演示稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`document_chunk_rows()` 对非对象 chunk 输出 `chunk_location=invalid`；对非字符串 `text` 输出 `text_preview=invalid` 和 `text_chars=0`；正常 chunk 的位置、vector_id 和摘要展示保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_chunk_rows_handle_malformed_entries_and_text -q` 失败，非对象 chunk 触发 `AttributeError: 'str' object has no attribute 'get'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_chunk_rows_handle_malformed_entries_and_text tests/test_frontend_api.py::test_document_chunk_rows_surface_vector_backlinks_and_preview -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`119 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_documents_tab_exposes_section_and_chunk_pagination_controls tests/test_api.py::test_streamlit_document_chunks_errors_show_payload_details -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1176 passed`。
