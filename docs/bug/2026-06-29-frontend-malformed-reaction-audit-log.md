# Frontend reaction audit log crashed on malformed entries

## 现象

- 触发命令、接口或页面：Streamlit 化学复核页调用 `reaction_audit_rows(reaction["audit_log"])` 渲染反应复核审计记录；审计列表里混入非对象条目，或 `field_changes` / 单个字段变更不是对象。
- 实际结果：`reaction_audit_rows()` 直接调用 `audit.get()`、`field_changes.items()` 和 `change.get()`，异常 payload 会触发 `AttributeError`，导致页面渲染失败。
- 期望结果：审计日志展示层应稳定降级，把异常条目显示为 `invalid` 行，并继续渲染同一日志里的有效字段变更。

## 原因

- 根因：展示层 helper 假设反应审计日志完全符合 API 契约，没有在靠近 Streamlit 渲染的位置校验嵌套对象类型。
- 影响范围：Streamlit 化学复核页的审计日志表格、导出前复核排障，以及接口契约漂移或历史脏数据下的演示稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`reaction_audit_rows()` 对非对象审计项输出 `field=invalid`；对非对象 `field_changes` 输出 `field=field_changes` 且 before/after 为 `invalid`；对单个非对象字段变更输出对应字段的 `invalid` 行，同时保留同一审计记录里的有效字段变更。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_audit_rows_handle_malformed_entries_and_field_changes -q` 失败，非对象审计项触发 `AttributeError: 'str' object has no attribute 'get'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_audit_rows_handle_malformed_entries_and_field_changes tests/test_frontend_api.py::test_reaction_audit_rows_flatten_field_changes_for_review -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_review_ui_exposes_review_fields -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`115 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1172 passed`。
