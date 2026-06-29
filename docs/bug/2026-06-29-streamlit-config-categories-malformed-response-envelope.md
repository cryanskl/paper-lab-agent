# Streamlit config categories crashed on malformed response envelope

## 现象

- 触发命令、接口或页面：Streamlit 配置页加载 `/categories` 后渲染分类表格和新增分类的父级选择器。
- 实际结果：当 `/categories` 返回 2xx JSON 对象但缺少 `items`、`total`、`page` 或 `page_size`，或这些字段类型异常时，配置页会在直接索引 `categories_response["items"]` 时崩溃。
- 期望结果：配置页在读取分类列表字段前先规范化分页 envelope；异常 envelope 显示为空分类列表，不影响配置页继续渲染。

## 原因

- 根因：配置页已经对 `/journals` 调用了 `paginated_response_state()`，但同一加载流程里的 `/categories` 仍直接读取响应字段，两个分页列表的异常响应处理不一致。
- 影响范围：分类管理、期刊/论文人工分类的配置入口、发布演示中的异常 API 响应处理，以及代理层返回不完整 JSON 时的前端稳定性。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：配置页在读取 `categories_response["items"]` 前调用 `paginated_response_state(categories_response, default_page_size=100)`，与期刊白名单列表保持一致。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_tab_normalizes_categories_response_envelope -q` 失败，配置页未规范化 `/categories` 响应 envelope。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_tab_normalizes_categories_response_envelope tests/test_api.py::test_streamlit_config_tab_normalizes_journals_response_envelope tests/test_api.py::test_streamlit_config_metadata_errors_show_payload_details tests/test_api.py::test_streamlit_config_tab_exposes_journal_pagination_controls tests/test_api.py::test_streamlit_config_tab_exposes_journal_and_category_management -q` 通过，5 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1233 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1233 passed。
