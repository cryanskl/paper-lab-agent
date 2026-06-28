# Streamlit reaction audit dataframe emitted Arrow type warnings

## 现象

- 触发页面：Streamlit Chemistry tab，加载反应集后展开 `audit_log` 表格。
- 实际结果：Streamlit 日志出现 Arrow 类型转换警告，提示 `after` 列混合字符串和布尔值后需要自动修复。
- 期望结果：审计日志表格展示列类型稳定，不在发布演示或本地验证时产生 dataframe 序列化噪音。

## 原因

- 根因：`reaction_audit_rows` 将 `field_changes.before/after` 原样传给 `st.dataframe`。
- 影响范围：化学库人工复核审计日志；当同一列同时包含字符串、布尔值或空值时触发。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：审计表格的 `before` 和 `after` 展示列统一转成文本；底层 API 返回的 audit JSON 不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_audit_rows_flatten_field_changes_for_review -q` 修复前失败，`before` 仍为 `None`，布尔值仍会原样进入审计表格行。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_audit_rows_flatten_field_changes_for_review tests/test_frontend_api.py::test_reaction_set_rows_label_export_state_and_review_progress tests/test_frontend_api.py::test_reaction_set_option_label_summarizes_review_and_export_state tests/test_frontend_api.py::test_reaction_set_option_label_uses_fallbacks_for_sparse_items -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`1078 passed`；`bash scripts/release_check.sh` 重新运行通过。
