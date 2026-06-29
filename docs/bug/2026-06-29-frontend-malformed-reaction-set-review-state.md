# Frontend reaction set review state crashed on malformed count fields

## 现象

- 触发命令、接口或页面：Streamlit 化学页加载反应集详情后，使用 `/api/v1/reaction-sets/{id}` 返回项渲染 `reaction_set_review_state()`；`reaction_count`、`verified_count`、`unverified_count` 或 `export_ready` 字段类型异常，例如计数字段是列表或字符串，`export_ready` 是字符串。
- 实际结果：`reaction_set_review_state()` 通过 `int_or_default()` 直接调用 `int(value)`，计数字段为列表时抛出 `TypeError`；`export_ready` 使用 `bool(...)` 时会把 `"yes"` 等字符串误展示为可导出。
- 期望结果：复核状态 helper 应使用稳定 fallback：异常计数字段回退到由 `reactions` 推导出的默认值，异常 `export_ready` 由计数和未复核数推导，避免误放开导出按钮。

## 原因

- 根因：展示层 helper 假设 reaction set 详情响应来自完整 API 契约，没有校验计数字段和导出闸门字段类型。
- 影响范围：Streamlit 化学页反应集复核摘要、未复核导出闸门、异常 API 响应或接口契约漂移时的复核流程。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`int_or_default()` 对异常、负数和布尔值回退默认值；`reaction_set_review_state()` 只有在 `export_ready` 是布尔值时信任该字段，否则由 `reaction_count > 0 and unverified_count == 0` 推导。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_set_review_state_handles_malformed_counts_and_export_ready -q` 失败，`reaction_count` 为列表时触发 `TypeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_set_review_state_handles_malformed_counts_and_export_ready tests/test_frontend_api.py::test_reaction_set_review_state_derives_unverified_counts_and_export_gate tests/test_frontend_api.py::test_reaction_set_review_state_blocks_empty_reaction_sets -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_review_ui_exposes_review_fields tests/test_api.py::test_streamlit_chemistry_export_blocks_empty_reaction_sets -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`114 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1171 passed`。
