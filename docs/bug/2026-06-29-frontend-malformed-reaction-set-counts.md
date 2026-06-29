# Frontend reaction set rows crashed on malformed count fields

## 现象

- 触发命令、接口或页面：Streamlit 化学页加载文档反应集后，使用 `/api/v1/documents/{id}/reaction-sets` 返回项渲染 `reaction_set_rows()` 表格；单个 reaction set 的 `reaction_count`、`verified_count`、`unverified_count` 或 `export_ready` 字段类型异常，例如计数字段是列表或字符串，`export_ready` 是字符串。
- 实际结果：`reaction_set_rows()` 直接调用 `int(item.get(...))`，计数字段为列表时抛出 `TypeError`；`export_ready` 使用 `bool(...)` 时会把 `"yes"` 等字符串误展示为 `True`。
- 期望结果：表格行 helper 应使用稳定 fallback：异常计数字段显示 `0`，异常 `export_ready` 显示 `False`，并继续生成 `export_state` 与 `review_progress`。

## 原因

- 根因：展示层 helper 假设 reaction set 计数字段来自完整 API 契约，没有校验字段类型和值。
- 影响范围：Streamlit 化学页反应集列表、异常 API 响应或接口契约漂移时的反应集复核与导出入口。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`reaction_set_rows()` 对 reaction set 计数字段使用非负整数校验和 `0` fallback，对 `export_ready` 使用严格布尔校验，避免 malformed reaction set item 触发崩溃或误展示。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_set_rows_handle_malformed_counts_and_export_state -q` 失败，`reaction_count` 为列表时触发 `TypeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_set_rows_handle_malformed_counts_and_export_state tests/test_frontend_api.py::test_reaction_set_rows_label_export_state_and_review_progress -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_tab_exposes_reaction_set_pagination_controls -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`109 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1166 passed`。
