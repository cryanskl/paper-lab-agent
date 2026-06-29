# Frontend RAG source selection crashed on malformed source options

## 现象

- 触发命令、接口或页面：Streamlit RAG 页在问答后使用 `st.selectbox(..., format_func=rag_source_option_label)` 展示引用来源，并对选中项调用 `source_preview.get("source_excerpt")` 预览原文片段；sources 列表里混入非对象条目，或选中项的 `source_excerpt` 不是字符串。
- 实际结果：`rag_source_option_label()` 直接调用 `source.get()`，非对象 source 会触发 `AttributeError`；即使标签降级，选中异常 source 后直接 `.get("source_excerpt")` 也会让页面崩溃。
- 期望结果：RAG 引用来源选择器应稳定降级：异常选项显示 `引用来源`，异常或非文本 excerpt 显示为空字符串，页面继续展示引用表和 raw RAG response。

## 原因

- 根因：`rag_source_rows()` 已经能把异常来源行降级成可展示表格行，但 selectbox 标签函数和选中项预览仍假设 source 是 API 契约对象。
- 影响范围：Streamlit RAG 问答引用定位、真实论文问答排障、接口契约漂移或历史脏数据下的演示稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：`rag_source_option_label()` 对非对象 source 返回 `引用来源`；新增 `rag_source_preview_excerpt()`，只在选中项为对象且 `source_excerpt` 为字符串时返回文本；Streamlit 使用该 helper 渲染 `st.code()`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_rag_source_option_label_handles_malformed_source tests/test_frontend_api.py::test_rag_source_preview_excerpt_handles_malformed_source_and_excerpt -q` 失败，非对象 source 触发 `AttributeError: 'str' object has no attribute 'get'`，且缺少 `rag_source_preview_excerpt`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_rag_tab_separates_answer_and_sources -q` 失败，Streamlit 尚未使用 `rag_source_preview_excerpt(source_preview)`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_rag_source_option_label_handles_malformed_source tests/test_frontend_api.py::test_rag_source_preview_excerpt_handles_malformed_source_and_excerpt tests/test_frontend_api.py::test_rag_source_option_label_combines_citation_and_location tests/test_frontend_api.py::test_rag_source_option_label_uses_stable_fallback -q` 通过，`4 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_rag_tab_separates_answer_and_sources -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1182 passed`。
