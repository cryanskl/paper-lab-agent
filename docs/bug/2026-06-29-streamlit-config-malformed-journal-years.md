# Streamlit config journal form crashed on malformed year values

## 现象

- 触发命令、接口或页面：Streamlit 配置页进入“更新期刊”表单时，会把选中 journal 的 `year_from` / `year_to` 转成 `number_input` 默认值。
- 实际结果：页面直接执行 `int(selected_journal.get("year_from") or 1990)` 和 `int(selected_journal.get("year_to") or 0)`；当历史数据、异常响应或接口漂移返回非数值字符串时，配置页会触发 `ValueError`，无法继续维护期刊白名单。
- 期望结果：异常年份应稳定降级：`year_from` 使用 `1990`，`year_to` 使用 `0`，页面继续展示更新表单。

## 原因

- 根因：配置页更新表单绕过了已有的 `int_or_default()` 类型保护，直接对 API 字段做 `int(...)` 转换。
- 影响范围：Streamlit 配置页、期刊白名单维护流程、包含 malformed 年份历史数据的本地数据库或异常 API 响应。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：Streamlit 配置页导入并使用 `int_or_default()` 设置 `year_from` / `year_to` 的编辑默认值，避免 malformed 年份字段阻塞页面渲染。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_tab_can_update_journal_year_range -q` 失败，配置页仍缺少 `int_or_default(...)` 并保留直接 `int(selected_journal.get(...))`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_tab_can_update_journal_year_range tests/test_api.py::test_streamlit_config_tab_exposes_journal_and_category_management tests/test_api.py::test_streamlit_config_tab_uses_journal_option_label_helper tests/test_api.py::test_streamlit_config_metadata_errors_show_payload_details tests/test_api.py::test_streamlit_config_tab_exposes_journal_pagination_controls -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1195 passed`。
