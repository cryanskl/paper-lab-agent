# Frontend category parent label crashed on malformed category items

## 现象

- 触发命令、接口或页面：Streamlit 配置页新增分类表单的父分类 selectbox 使用 `/api/v1/categories` 返回项渲染 `category_parent_option_label()`，但单个 category 缺少 `id` 或 `slug` 类型异常，例如 `slug` 是列表。
- 实际结果：`category_parent_option_label()` 直接访问 `category["id"]`，缺失时抛出 `KeyError`；异常 `slug` 也可能被误展示为正常值。
- 期望结果：label helper 应使用稳定 fallback：缺失或异常 `id` 显示 `#-`，异常 `slug` 显示 `category`，`None` 仍表示“无”。

## 原因

- 根因：展示层 helper 假设 category 项来自完整 API 契约，没有校验 option item 的字段类型和值。
- 影响范围：Streamlit 配置页新增分类表单的父分类选择器、异常 API 响应或接口契约漂移时的分类管理流程。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`category_parent_option_label()` 对 `id`、`slug` 使用类型校验和稳定 fallback，避免 malformed category item 触发崩溃或误展示。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_category_parent_option_label_handles_malformed_category_items -q` 失败，缺失 `id` 触发 `KeyError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_category_parent_option_label_handles_malformed_category_items tests/test_frontend_api.py::test_category_parent_option_label_returns_none_label tests/test_frontend_api.py::test_category_parent_option_label_summarizes_category_identity -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_tab_uses_category_parent_option_label_helper -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`107 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1164 passed`。
