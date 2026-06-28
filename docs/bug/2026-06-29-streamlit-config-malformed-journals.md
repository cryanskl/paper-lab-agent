# Streamlit config page crashed on malformed journal items

## 现象

- 触发命令、接口或页面：Streamlit 配置页调用 `/api/v1/journals` 后，直接把 `journals_response["items"]` 作为期刊白名单表格和“更新期刊”下拉的数据源。
- 实际结果：表格 helper 能跳过非对象，但更新下拉的 `format_func=journal_option_label`、checkbox key、更新 URL 和停用 URL 会继续使用原始 journal；当列表混入非对象、缺少合法 `id`、字符串 `id`、bool `id` 或空白 `name` 的条目时，页面会在渲染或交互时崩溃。
- 期望结果：进入配置页期刊表格和更新下拉的 journal 必须带有非 bool 整数 `id` 和非空字符串 `name`；异常条目被跳过，分页和 total 仍照常显示。

## 原因

- 根因：配置页期刊列表直接使用 `/journals` 原始 items，没有在 UI 使用前做最小结构校验。
- 影响范围：配置页期刊白名单表格、期刊更新下拉、更新/停用期刊操作，以及异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `journal_items()`，仅保留带非 bool 整数 `id` 和非空字符串 `name` 的 journal；配置页 `journals_all` 改为使用过滤后的列表。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_journal_items_skip_malformed_items tests/test_api.py::test_streamlit_config_tab_uses_filtered_journal_items -q` 失败，helper 缺失且配置页仍直接使用 `journals_response["items"]`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_journal_items_skip_malformed_items tests/test_api.py::test_streamlit_config_tab_uses_filtered_journal_items tests/test_api.py::test_streamlit_config_tab_normalizes_journal_keywords_for_dataframe tests/test_api.py::test_streamlit_config_metadata_errors_show_payload_details tests/test_api.py::test_streamlit_config_tab_exposes_journal_pagination_controls tests/test_api.py::test_streamlit_config_tab_can_update_journal_year_range tests/test_api.py::test_streamlit_config_tab_can_create_journal_with_year_to tests/test_api.py::test_streamlit_config_tab_uses_category_parent_option_label_helper -q` 通过，8 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1214 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1214 passed`。
