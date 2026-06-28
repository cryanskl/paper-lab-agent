# Streamlit search page crashed on malformed manual category options

## 现象

- 触发命令、接口或页面：Streamlit 搜索页加载 `/api/v1/categories` 后，用返回的 `items` 构造分类筛选和论文的“人工覆盖分类” multiselect。
- 实际结果：页面直接把原始 category 列表用于 `category_slugs`、`category_options_by_slug` 和 `paper_category_option_label()`；当列表混入非对象、缺少 `id` 或缺少 `slug` 的条目时，筛选渲染、默认值映射或保存分类 ID 都可能触发异常。
- 期望结果：搜索页只使用能安全显示、映射和提交的 category 对象；异常条目被跳过，label helper 对非对象输入返回稳定 fallback。

## 原因

- 根因：搜索页没有在 UI 使用前过滤 `/categories` 返回的条目，`paper_category_option_label()` 也假设输入一定是 dict。
- 影响范围：搜索页分类筛选、论文人工分类覆盖流程、异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `paper_category_options()`，仅保留带整数 `id` 和非空字符串 `slug` 的 category 对象；`paper_category_option_label()` 对非对象输入返回 `category · category`；搜索页加载 categories 后先经过该 helper，再用于筛选和人工分类 multiselect。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_category_options_skip_malformed_items tests/test_frontend_api.py::test_paper_category_option_label_handles_non_object_item tests/test_api.py::test_streamlit_search_categories_use_filtered_options -q` 失败，`paper_category_options` 缺失、非对象 label 触发 `AttributeError`，搜索页仍直接使用原始 categories。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_category_options_skip_malformed_items tests/test_frontend_api.py::test_paper_category_option_label_handles_non_object_item tests/test_frontend_api.py::test_paper_category_option_label_summarizes_slug_and_name tests/test_frontend_api.py::test_paper_category_option_label_uses_fallback_name tests/test_api.py::test_streamlit_search_categories_use_filtered_options -q` 通过，`5 passed`。
- 搜索页契约：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_search_filter_metadata_errors_show_payload_details tests/test_api.py::test_streamlit_search_categories_use_filtered_options tests/test_api.py::test_streamlit_search_results_show_dedupe_strategy tests/test_api.py::test_streamlit_search_tab_exposes_sort_control tests/test_api.py::test_streamlit_search_results_can_trigger_classification tests/test_api.py::test_streamlit_search_classification_errors_show_payload_details tests/test_api.py::test_streamlit_search_results_can_override_categories_manually tests/test_api.py::test_streamlit_search_manual_category_errors_show_payload_details -q` 通过，`8 passed`。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，`1202 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1202 passed`。
