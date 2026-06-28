# Frontend reaction set label crashed on malformed reaction set items

## 现象

- 触发命令、接口或页面：Streamlit 化学页的文档反应集 selectbox 使用 `/api/v1/documents/{id}/reaction-sets` 返回项渲染 `reaction_set_option_label()`，但单个 reaction set 缺少 `id` 或字段类型异常，例如 `document_id`、`status`、`unverified_count`、`name` 是列表，`export_ready` 是字符串。
- 实际结果：`reaction_set_option_label()` 直接访问 `item["id"]`，缺失时抛出 `KeyError`；`export_ready` 使用 `bool(...)` 时会把 `"yes"` 等字符串误展示为 `True`。
- 期望结果：label helper 应使用稳定 fallback：缺失或异常 `id` 显示 `#-`，异常 `document_id` 不展示 doc 前缀，异常 `status` 显示 `unknown`，异常 `export_ready` 显示 `False`，异常 `unverified_count` 显示 `0`，异常 `name` 显示 `Reaction set`。

## 原因

- 根因：展示层 helper 假设 reaction set 项来自完整 API 契约，没有校验 option item 的字段类型和值。
- 影响范围：Streamlit 化学页反应集选择器、异常 API 响应或接口契约漂移时的反应集复核与导出流程。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`reaction_set_option_label()` 对 `id`、`document_id`、`status`、`export_ready`、`unverified_count`、`name` 使用类型校验和稳定 fallback，避免 malformed reaction set item 触发崩溃或误展示。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_set_option_label_handles_malformed_items -q` 失败，缺失 `id` 触发 `KeyError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_set_option_label_handles_malformed_items tests/test_frontend_api.py::test_reaction_set_option_label_summarizes_review_and_export_state tests/test_frontend_api.py::test_reaction_set_option_label_uses_fallbacks_for_sparse_items -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_tab_can_select_document_for_reaction_sets -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`108 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1165 passed`。
