# Streamlit chemistry reaction set selectors accepted malformed items

## 现象

- 触发命令、接口或页面：Streamlit 化学库页加载 `/api/v1/documents/{document_id}/reaction-sets` 后，用 `reaction_set_rows()` 渲染 dataframe，并用 `reaction_set_options()` 生成 `document_reaction_sets` selectbox。
- 实际结果：`reaction_set_rows()` 对非对象条目直接调用 `.get()`，会触发 `AttributeError`；`reaction_set_options()` 只过滤非对象，缺少 `id`、字符串 `id` 或 bool `id` 的反应集 dict 仍会进入 selectbox，后续 `selected_reaction_set["id"]` 可能触发异常或误用非法 ID。
- 期望结果：反应集列表渲染遇到异常条目应稳定降级；进入 selectbox 的反应集必须带有非 bool 整数 `id`。

## 原因

- 根因：反应集 dataframe 和选择器 helper 对 API items 的结构要求不一致；行渲染没有保护非对象输入，选择器没有校验 `id`。
- 影响范围：化学库页文档反应集加载、反应集详情选择，以及异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`reaction_set_rows()` 对非对象条目输出稳定的 invalid fallback 行；`reaction_set_options()` 只返回 dict 且 `id` 为非 bool 整数的反应集。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_set_rows_handle_non_object_items tests/test_frontend_api.py::test_reaction_set_options_skip_items_without_valid_id -q` 失败，非对象行触发 `AttributeError`，缺失/非法 `id` 的 dict 仍进入选项。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_set_rows_handle_non_object_items tests/test_frontend_api.py::test_reaction_set_options_skip_items_without_valid_id tests/test_frontend_api.py::test_reaction_set_rows_label_export_state_and_review_progress tests/test_frontend_api.py::test_reaction_set_rows_handle_malformed_counts_and_export_state tests/test_frontend_api.py::test_reaction_set_options_skip_malformed_items tests/test_frontend_api.py::test_reaction_set_option_label_handles_malformed_items tests/test_frontend_api.py::test_reaction_set_option_label_handles_non_object_item -q` 通过，`7 passed`。
- Streamlit 契约：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_tab_exposes_reaction_set_pagination_controls tests/test_api.py::test_streamlit_chemistry_document_reaction_sets_show_empty_state tests/test_api.py::test_streamlit_chemistry_tab_can_select_document_for_reaction_sets tests/test_api.py::test_streamlit_chemistry_tab_does_not_auto_load_missing_reaction_set -q` 通过，`4 passed`。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，`1205 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1205 passed`。
