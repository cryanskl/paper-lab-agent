# Streamlit config category parent selector crashed on malformed category items

## 现象

- 触发命令、接口或页面：Streamlit 配置页创建分类时，会把 `/api/v1/categories` 的 `items` 拼成 `parent_options` 并用 `category_parent_option_label()` 渲染 parent selector。
- 实际结果：页面直接使用 `[None] + categories_all`，`category_parent_option_label()` 只处理 `None` 和 dict-like category；当列表混入非对象条目时，format function 会触发 `AttributeError`。如果 malformed 项被选中，提交 payload 里的 `parent_choice["id"]` 也会崩溃。
- 期望结果：parent selector 应稳定降级：只保留有效 category 对象作为可选父分类，非对象条目被跳过，label helper 对异常输入也返回稳定 fallback。

## 原因

- 根因：配置页 category parent 选择器缺少 options 过滤，label helper 也未保护非对象输入。
- 影响范围：Streamlit 配置页、分类创建流程、异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `category_parent_options()` 过滤 parent selector 选项；`category_parent_option_label()` 对非对象值返回 `#- category`；Streamlit 配置页改为使用过滤后的 options。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_category_parent_options_skip_malformed_items tests/test_frontend_api.py::test_category_parent_option_label_handles_non_object_item tests/test_api.py::test_streamlit_config_category_parent_options_skip_malformed_items -q` 失败，`category_parent_options` 缺失且非对象 label 触发 `AttributeError`，配置页仍使用 `[None] + categories_all`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_category_parent_options_skip_malformed_items tests/test_frontend_api.py::test_category_parent_option_label_handles_non_object_item tests/test_frontend_api.py::test_category_parent_option_label_returns_none_label tests/test_frontend_api.py::test_category_parent_option_label_summarizes_category_identity tests/test_frontend_api.py::test_category_parent_option_label_handles_malformed_category_items tests/test_api.py::test_streamlit_config_category_parent_options_skip_malformed_items -q` 通过，`6 passed`。
- 配置页契约：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_tab_exposes_journal_and_category_management tests/test_api.py::test_streamlit_config_tab_uses_journal_option_label_helper tests/test_api.py::test_streamlit_config_tab_normalizes_journal_keywords_for_dataframe tests/test_api.py::test_streamlit_config_metadata_errors_show_payload_details tests/test_api.py::test_streamlit_config_tab_exposes_journal_pagination_controls tests/test_api.py::test_streamlit_config_tab_can_update_journal_year_range tests/test_api.py::test_streamlit_config_tab_can_create_journal_with_year_to tests/test_api.py::test_streamlit_config_create_errors_show_payload_details tests/test_api.py::test_streamlit_config_category_parent_options_skip_malformed_items -q` 通过，`9 passed`。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，`1199 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1199 passed`。
