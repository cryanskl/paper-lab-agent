# Streamlit search categories crashed on malformed response envelope

## 现象

- 触发命令、接口或页面：Streamlit 检索页加载 `/categories` 后渲染分类筛选器和人工覆盖分类选项。
- 实际结果：当 `/categories` 返回 2xx JSON 对象但缺少 `items`、`total`、`page` 或 `page_size`，或这些字段类型异常时，检索页会在内联读取 `api_get("/categories")["items"]` 时崩溃。
- 期望结果：检索页在读取分类筛选列表前先规范化分页 envelope；异常 envelope 显示为空分类选项，不影响检索页继续渲染。

## 原因

- 根因：检索页的分类筛选元数据仍以内联方式直接读取 `/categories` 的 `items` 字段，没有复用配置页和期刊筛选已使用的 `paginated_response_state()`。
- 影响范围：论文检索分类筛选、人工覆盖分类、发布演示中的异常 API 响应处理，以及代理层返回不完整 JSON 时的前端稳定性。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：检索页先保存 `search_categories_response`，再调用 `paginated_response_state(search_categories_response, default_page_size=20)`，最后从规范化后的 `items` 生成分类筛选选项。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_search_tab_normalizes_categories_response_envelope -q` 失败，检索页仍内联读取 `/categories` 响应 `items`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_search_tab_normalizes_categories_response_envelope tests/test_api.py::test_streamlit_search_filter_metadata_errors_show_payload_details tests/test_api.py::test_streamlit_search_categories_use_filtered_options tests/test_api.py::test_streamlit_search_journals_use_filtered_options tests/test_api.py::test_streamlit_search_tab_normalizes_journals_response_envelope -q` 通过，5 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1235 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1235 passed。
