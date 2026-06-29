# Streamlit config journal table crashed on malformed journal items

## 现象

- 触发命令、接口或页面：Streamlit 配置页加载期刊白名单表格时，会把 `/api/v1/journals` 的 `items` 渲染为 `journals_table`。
- 实际结果：页面 inline 使用 `{**journal, ...}` 展开每个 journal；当 API 响应、历史数据或契约漂移让列表中混入非对象条目时，表格构造会触发 `TypeError`，导致配置页无法展示。
- 期望结果：期刊表格应稳定降级：跳过非对象 journal，保留有效条目，并继续把 dict/list `keywords` 格式化为 JSON 文本用于表格展示。

## 原因

- 根因：配置页表格格式化逻辑直接写在 Streamlit 页面里，只假设每个 journal 都是对象；已有的 `journal_option_label()` 防护没有覆盖表格行构造。
- 影响范围：Streamlit 配置页、期刊白名单查看与维护流程、异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `journal_table_rows()`，跳过非对象条目并集中处理 `keywords` 展示格式；Streamlit 配置页改为调用该 helper，移除 inline `**journal` 展开。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_journal_table_rows_skip_malformed_items_and_format_keywords tests/test_api.py::test_streamlit_config_tab_normalizes_journal_keywords_for_dataframe -q` 失败，`journal_table_rows` 缺失且配置页仍未使用该 helper。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_journal_table_rows_skip_malformed_items_and_format_keywords tests/test_api.py::test_streamlit_config_tab_normalizes_journal_keywords_for_dataframe -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`138 passed`；配置页契约测试组通过，`8 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1196 passed`。
