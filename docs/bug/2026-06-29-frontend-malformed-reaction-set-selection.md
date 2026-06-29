# Frontend reaction set selection crashed on malformed reaction set options

## 现象

- 触发命令、接口或页面：Streamlit 化学库页加载文档反应集后，把 `/documents/{id}/reaction-sets` 返回的 `items` 直接交给 `st.selectbox("document_reaction_sets", ..., format_func=reaction_set_option_label)`，并在选中后读取 `selected_reaction_set["id"]`。
- 实际结果：`reaction_set_option_label()` 直接调用 `item.get()`，非对象 reaction set 会触发 `AttributeError`；即使标签降级，异常项仍可能进入选中态并在 `["id"]` 读取时崩溃。
- 期望结果：反应集选择器应稳定降级：选项构建阶段跳过非对象 reaction set，label helper 对异常项返回稳定占位，页面继续展示反应集表或空状态。

## 原因

- 根因：`reaction_set_rows()` 已可将异常反应集行降级为表格内容，但 selectbox 选项和 label helper 仍假设接口返回的每个 item 都是反应集对象。
- 影响范围：化学库复核入口、反应集加载、导出前人工复核工作流，以及接口契约漂移或历史脏数据下的演示稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `reaction_set_options()`，只返回有效对象；`reaction_set_option_label()` 对非对象 item 返回 `#- · unknown · export_ready False · 未复核 0 · Reaction set`；Streamlit 使用过滤后的 `reaction_set_choices` 控制空态和 selectbox。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_set_options_skip_malformed_items tests/test_frontend_api.py::test_reaction_set_option_label_handles_non_object_item -q` 失败，缺少 `reaction_set_options`，且非对象 item 触发 `AttributeError: 'str' object has no attribute 'get'`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_tab_exposes_reaction_set_pagination_controls -q` 失败，Streamlit 尚未使用 `reaction_set_options(reaction_set_items)`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_set_options_skip_malformed_items tests/test_frontend_api.py::test_reaction_set_option_label_handles_non_object_item tests/test_frontend_api.py::test_reaction_set_option_label_summarizes_review_and_export_state tests/test_frontend_api.py::test_reaction_set_option_label_uses_fallbacks_for_sparse_items tests/test_frontend_api.py::test_reaction_set_option_label_handles_malformed_items -q` 通过，`5 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_tab_exposes_reaction_set_pagination_controls tests/test_api.py::test_streamlit_chemistry_document_reaction_sets_show_empty_state -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1188 passed`。
