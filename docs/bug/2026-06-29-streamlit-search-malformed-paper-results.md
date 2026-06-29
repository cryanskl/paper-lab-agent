# Streamlit search page crashed on malformed paper result items

## 现象

- 触发命令、接口或页面：Streamlit 搜索页调用 `/api/v1/papers` 后，直接遍历 `papers["items"]` 渲染结果卡片。
- 实际结果：结果卡片直接使用 `paper["title"]`、`paper["id"]` 生成标题、按钮 key 和 `/papers/{paper['id']}` 相关 API URL；当列表混入非对象、缺少 `id`、字符串 `id`、bool `id` 或缺少/空白 `title` 的条目时，页面会在渲染或交互时崩溃。
- 期望结果：进入搜索结果卡片的 paper 必须带有非 bool 整数 `id` 和非空字符串 `title`；异常条目被跳过，API total 仍照常显示。

## 原因

- 根因：搜索结果循环直接使用 `/papers` 原始 items，没有在 UI 使用前做最小结构校验。
- 影响范围：搜索页结果卡片、触发分类、重新解析 OA、人工分类覆盖，以及异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `paper_search_result_items()`，仅保留带非 bool 整数 `id` 和非空字符串 `title` 的 paper；搜索页结果卡片循环改为遍历过滤后的 `display_papers`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_search_result_items_skip_malformed_items tests/test_api.py::test_streamlit_search_results_use_filtered_paper_items -q` 失败，helper 缺失且搜索页仍直接遍历 `papers["items"]`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_search_result_items_skip_malformed_items tests/test_api.py::test_streamlit_search_results_use_filtered_paper_items tests/test_api.py::test_streamlit_search_results_show_dedupe_strategy tests/test_api.py::test_streamlit_search_results_can_trigger_classification tests/test_api.py::test_streamlit_search_results_can_override_categories_manually tests/test_api.py::test_streamlit_search_results_can_resolve_oa_manually -q` 通过，6 passed。
- 搜索页契约：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_search_filter_metadata_errors_show_payload_details tests/test_api.py::test_streamlit_search_journals_use_filtered_options tests/test_api.py::test_streamlit_search_categories_use_filtered_options tests/test_api.py::test_streamlit_search_results_show_dedupe_strategy tests/test_api.py::test_streamlit_search_results_use_filtered_paper_items tests/test_api.py::test_streamlit_search_tab_exposes_sort_control tests/test_api.py::test_streamlit_search_results_can_trigger_classification tests/test_api.py::test_streamlit_search_classification_errors_show_payload_details tests/test_api.py::test_streamlit_search_results_can_override_categories_manually tests/test_api.py::test_streamlit_search_manual_category_errors_show_payload_details tests/test_api.py::test_streamlit_search_results_can_resolve_oa_manually -q` 通过，11 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1211 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1211 passed`。
