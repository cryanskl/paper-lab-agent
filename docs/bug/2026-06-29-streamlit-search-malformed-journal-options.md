# Streamlit search page crashed on malformed journal filter options

## 现象

- 触发命令、接口或页面：Streamlit 搜索页加载 `/api/v1/journals?active=true` 后，用返回的 `items` 构造期刊筛选下拉框。
- 实际结果：页面直接执行 `[j["name"] for j in journals]`，并在选择具体期刊后用 `next(j["id"] for j in journals if j["name"] == journal_choice)` 生成 `journal_id`。当列表混入非对象、缺少 `name`、缺少 `id`、字符串 `id` 或 bool `id` 的条目时，页面可能在渲染筛选器或提交搜索参数时崩溃。
- 期望结果：进入搜索页期刊筛选的 journal 必须带有非 bool 整数 `id` 和非空字符串 `name`；异常条目被跳过，搜索页仍能稳定展示“全部”和有效期刊。

## 原因

- 根因：搜索页期刊筛选直接使用 `/journals` 原始 items，没有在 UI 使用前做最小结构校验。
- 影响范围：搜索页期刊筛选、论文检索参数构造，以及异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `paper_search_journal_options()`，仅保留带非 bool 整数 `id` 和非空字符串 `name` 的 journal；搜索页加载 active journals 后先经过该 helper，再构造筛选器和 `journal_id`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_search_journal_options_skip_malformed_items tests/test_api.py::test_streamlit_search_filter_metadata_errors_show_payload_details tests/test_api.py::test_streamlit_search_journals_use_filtered_options -q` 失败，helper 缺失且搜索页仍直接使用原始 `/journals` items。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_search_journal_options_skip_malformed_items tests/test_frontend_api.py::test_journal_option_label_summarizes_whitelist_status tests/test_frontend_api.py::test_journal_table_rows_skip_malformed_items_and_format_keywords tests/test_api.py::test_streamlit_search_filter_metadata_errors_show_payload_details tests/test_api.py::test_streamlit_search_journals_use_filtered_options -q` 通过，`5 passed`。
- 搜索页契约：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_search_filter_metadata_errors_show_payload_details tests/test_api.py::test_streamlit_search_journals_use_filtered_options tests/test_api.py::test_streamlit_search_categories_use_filtered_options tests/test_api.py::test_streamlit_search_results_show_dedupe_strategy tests/test_api.py::test_streamlit_search_tab_exposes_sort_control tests/test_api.py::test_streamlit_search_results_can_trigger_classification tests/test_api.py::test_streamlit_search_classification_errors_show_payload_details tests/test_api.py::test_streamlit_search_results_can_override_categories_manually tests/test_api.py::test_streamlit_search_manual_category_errors_show_payload_details -q` 通过，`9 passed`。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，`1209 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1209 passed`。
