# Streamlit reaction review accepted reactions with invalid ids

## 现象

- 触发命令、接口或页面：Streamlit 化学库页加载反应集详情后，用 `reaction_set_review_state()` 和 `reaction_review_list_state()` 生成复核卡片列表。
- 实际结果：`reaction_items()` 只过滤非对象条目；缺少 `id`、字符串 `id` 或 bool `id` 的 reaction dict 仍会进入复核卡片。页面随后用 `reaction['id']` 生成组件 key 和 `/reactions/{reaction['id']}/verify` 保存 URL，可能触发 `KeyError`、保存到非法 URL，或把 bool 误当作整数。
- 期望结果：进入复核 UI 的 reaction 必须带有非 bool 整数 `id`；异常条目被跳过，复核计数和未复核筛选只基于可操作 reaction。

## 原因

- 根因：复核 UI 的共享 helper `reaction_items()` 缺少最小结构校验，只检查 `isinstance(reaction, dict)`。
- 影响范围：化学库页反应复核卡片、未复核筛选、保存复核操作，以及异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`reaction_items()` 现在只返回 dict 且 `id` 为非 bool 整数的 reaction；`reaction_set_review_state()`、`reaction_review_list_state()` 和 `reaction_review_rows()` 自动复用该过滤。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_set_review_state_skips_reactions_without_valid_id tests/test_frontend_api.py::test_reaction_review_list_state_skips_reactions_without_valid_id -q` 失败，缺失/非法 `id` 的 reaction 进入了复核状态和未复核列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_set_review_state_skips_reactions_without_valid_id tests/test_frontend_api.py::test_reaction_review_list_state_skips_reactions_without_valid_id tests/test_frontend_api.py::test_reaction_set_review_state_skips_malformed_reactions tests/test_frontend_api.py::test_reaction_set_review_state_derives_unverified_counts_and_export_gate tests/test_frontend_api.py::test_reaction_review_list_state_skips_malformed_reactions tests/test_frontend_api.py::test_reaction_review_list_state_summarizes_filtered_review_scope tests/test_frontend_api.py::test_reaction_review_rows_can_focus_unverified_source_metadata -q` 通过，`7 passed`。
- Streamlit 契约：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_review_ui_exposes_review_fields tests/test_api.py::test_streamlit_chemistry_review_uses_controlled_type_options tests/test_api.py::test_streamlit_chemistry_review_errors_show_payload_details tests/test_api.py::test_streamlit_chemistry_review_surfaces_save_success_state tests/test_api.py::test_streamlit_chemistry_audit_log_surfaces_field_changes -q` 通过，`5 passed`。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，`1207 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1207 passed`。
