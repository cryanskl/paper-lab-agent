# Frontend document section rows crashed on malformed section payloads

## 现象

- 触发命令、接口或页面：Streamlit 文档页加载 `/api/v1/documents/{id}/sections` 后，调用 `document_section_rows()` 渲染章节表；章节列表里混入非对象条目，或单条章节的 `content` 不是字符串。
- 实际结果：`document_section_rows()` 直接调用 `section.get()`，非对象条目触发 `AttributeError`；非字符串 `content` 会继续传入 `summarize_text()` 并在 `.split()` 上崩溃。
- 期望结果：章节表展示层应稳定降级：异常章节显示为 `invalid` 行，异常正文显示 `content_preview=invalid` 且 `content_chars=0`，同一页里的有效章节继续展示。

## 原因

- 根因：展示层 helper 假设章节列表完全符合 API 契约，没有在 Streamlit 渲染边界校验章节条目和 `content` 类型。
- 影响范围：Streamlit 文档页章节浏览、GROBID/本地 fallback 解析结果排障，以及接口契约漂移或历史脏数据下的演示稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`document_section_rows()` 对非对象章节输出 `section_location=invalid`；对非字符串 `content` 输出 `content_preview=invalid` 和 `content_chars=0`；正常章节的位置和摘要展示保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_section_rows_handle_malformed_entries_and_content -q` 失败，非对象章节触发 `AttributeError: 'str' object has no attribute 'get'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_section_rows_handle_malformed_entries_and_content tests/test_frontend_api.py::test_document_section_rows_surface_location_and_preview -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`116 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_documents_tab_exposes_section_and_chunk_pagination_controls tests/test_api.py::test_streamlit_document_sections_errors_show_payload_details -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1173 passed`。
