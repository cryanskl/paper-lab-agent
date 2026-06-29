# Frontend journal option label crashed on malformed journal items

## 现象

- 触发命令、接口或页面：Streamlit 配置页的期刊 selectbox 使用 `/api/v1/journals` 返回项渲染 `journal_option_label()`，但单个 journal 缺少 `id` 或字段类型异常，例如 `name` 是列表、`active` 是字符串。
- 实际结果：`journal_option_label()` 直接访问 `journal["id"]`，缺失时抛出 `KeyError`；异常 `name` / `active` 也可能被误展示为正常值。
- 期望结果：label helper 应使用稳定 fallback：缺失或异常 `id` 显示 `#-`，异常 `name` 显示 `Journal`，`active` 只有布尔值才按原值展示，否则为 `False`。

## 原因

- 根因：展示层 helper 假设 journal 项来自完整 API 契约，没有校验 option item 的字段类型和值。
- 影响范围：Streamlit 配置页期刊选择器、异常 API 响应或接口契约漂移时的期刊管理表单。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`journal_option_label()` 对 `id`、`name`、`active` 使用类型校验和稳定 fallback，避免 malformed journal item 触发崩溃或误展示。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_journal_option_label_handles_malformed_journal_items -q` 失败，缺失 `id` 触发 `KeyError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_journal_option_label_handles_malformed_journal_items tests/test_frontend_api.py::test_journal_option_label_uses_unknown_name_and_false_active_fallback tests/test_frontend_api.py::test_journal_option_label_summarizes_whitelist_status -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_tab_uses_journal_option_label_helper -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`106 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1163 passed`。
