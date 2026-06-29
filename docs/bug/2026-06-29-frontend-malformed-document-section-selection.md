# Frontend document section selection crashed on malformed section options

## 现象

- 触发命令、接口或页面：Streamlit 文档页“章节”tab 使用 `st.selectbox(..., format_func=document_section_option_label)` 展示 sections，并对选中项调用 `section_preview.get("title")` 和 `section_preview.get("content")` 预览内容；sections 列表里混入非对象条目，或选中项的 `title` / `content` 不是字符串。
- 实际结果：`document_section_option_label()` 直接调用 `section.get()`，非对象 section 会触发 `AttributeError`；即使标签降级，选中异常 section 后直接 `.get()` 也会让页面崩溃。
- 期望结果：section 选择器应稳定降级：异常选项显示 `invalid. Section`，异常标题显示 `Section`，异常或非文本内容显示为空字符串，页面继续展示章节表和其它状态。

## 原因

- 根因：章节表格展示已经对非对象 section 和非文本 content 做了降级，但 selectbox 标签函数和选中项预览仍假设 section 是 API 契约对象。
- 影响范围：Streamlit 文档页章节浏览、GROBID 解析结果排障、历史脏数据或接口契约漂移下的演示稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：`document_section_option_label()` 对非对象 section 返回 `invalid. Section`；新增 `document_section_preview_title()` 和 `document_section_preview_content()`，只在选中项为对象且对应字段为字符串时返回文本；Streamlit 使用这些 helper 渲染标题和内容。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_section_option_label_handles_malformed_section tests/test_frontend_api.py::test_document_section_preview_fields_handle_malformed_section_and_content -q` 失败，非对象 section 触发 `AttributeError: 'str' object has no attribute 'get'`，且缺少 `document_section_preview_title`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_documents_tab_exposes_preview_and_index_status -q` 失败，Streamlit 尚未使用 `document_section_preview_title(section_preview)`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_section_option_label_handles_malformed_section tests/test_frontend_api.py::test_document_section_preview_fields_handle_malformed_section_and_content tests/test_frontend_api.py::test_document_section_option_label_uses_sequence_and_title tests/test_frontend_api.py::test_document_section_option_label_falls_back_to_type_and_id tests/test_api.py::test_streamlit_documents_tab_exposes_preview_and_index_status -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1180 passed`。
