# Streamlit search page crashed on malformed paper categories

## 现象

- 触发命令、接口或页面：Streamlit 搜索页渲染论文卡片的“人工覆盖分类”区域时，直接把 `paper.get("categories")` 转成 `set`。
- 实际结果：当 `categories` 是 bool、字符串、对象，或列表中包含 list/dict 等不可哈希条目时，页面会在渲染默认分类时崩溃。
- 期望结果：默认分类只从非空字符串 slug 中生成；异常条目被忽略。

## 原因

- 根因：搜索结果卡片直接使用 `/papers` 原始 `categories` 字段，没有在生成 `current_category_slugs` 前做类型校验。
- 影响范围：搜索页结果卡片、人工分类覆盖下拉，以及异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `paper_category_slugs()`，仅保留非空字符串 slug；搜索页人工分类默认值改为使用过滤后的 slug 集合。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_category_slugs_skip_malformed_categories tests/test_api.py::test_streamlit_search_manual_category_defaults_use_filtered_slugs -q` 失败，helper 缺失且搜索页仍直接 `set(paper.get("categories") or [])`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_category_slugs_skip_malformed_categories tests/test_api.py::test_streamlit_search_manual_category_defaults_use_filtered_slugs tests/test_api.py::test_streamlit_search_results_can_override_categories_manually tests/test_api.py::test_streamlit_search_manual_category_errors_show_payload_details -q` 通过，4 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1218 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1218 passed。
