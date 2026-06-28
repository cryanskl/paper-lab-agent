# Frontend reaction review list crashed on malformed reaction items

## 现象

- 触发命令、接口或页面：Streamlit 化学库页加载反应集详情后，`reaction_set_review_state()`、`reaction_review_list_state()` 和 `reaction_review_rows()` 会消费 `detail["reactions"]`，并在复核卡片和未复核表格中展示每条 reaction；reactions 列表里混入非对象条目。
- 实际结果：三个 helper 都直接调用 `reaction.get(...)`，非对象 reaction 会触发 `AttributeError`，导致复核面板无法展示，也无法继续人工复核或导出。
- 期望结果：复核入口应稳定降级：只展示和编辑有效 reaction 对象，异常 reaction 条目被跳过，页面继续展示有效反应、未复核摘要和导出闸门信息。

## 原因

- 根因：化学库复核 helper 假设后端返回的 `reactions` 全部是对象；此前只硬化了 reaction set 选择器，尚未保护进入复核面板后的 reaction 列表。
- 影响范围：化学库复核 UI、未复核反应表格、导出前人工复核流程，以及接口契约漂移或历史脏数据下的演示稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：新增 `reaction_items()`，只保留有效 reaction 对象；`reaction_set_review_state()`、`reaction_review_list_state()` 和 `reaction_review_rows()` 共用该过滤逻辑，避免异常 reaction 进入复核卡片和表格渲染。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_review_rows_skip_malformed_reactions tests/test_frontend_api.py::test_reaction_review_list_state_skips_malformed_reactions tests/test_frontend_api.py::test_reaction_set_review_state_skips_malformed_reactions -q` 失败，三个 helper 都在非对象 reaction 上触发 `AttributeError: 'str' object has no attribute 'get'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_review_rows_skip_malformed_reactions tests/test_frontend_api.py::test_reaction_review_list_state_skips_malformed_reactions tests/test_frontend_api.py::test_reaction_set_review_state_skips_malformed_reactions tests/test_frontend_api.py::test_reaction_review_rows_can_focus_unverified_source_metadata tests/test_frontend_api.py::test_reaction_review_list_state_summarizes_filtered_review_scope tests/test_frontend_api.py::test_reaction_set_review_state_derives_unverified_counts_and_export_gate -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1191 passed`。
