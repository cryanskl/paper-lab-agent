# Frontend release display split malformed readiness lists into characters

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `release_readiness`，其中 `demo_data_missing`、`failed_workflows` 或 `storage_errors` 不是列表而是字符串，例如 `"documents>=1"`。
- 实际结果：前端展示函数会按字符串逐字符迭代，侧边栏 blocker 变成 `d`、`o`、`c` 等字符，诊断信号不可读。
- 期望结果：malformed readiness list 应作为 `invalid` blocker 显示，避免异常 API 响应导致前端发布就绪诊断失真。

## 原因

- 根因：`app/frontend_api.py` 的 `release_readiness_display_state()` 只有 `config_warning_codes` 使用严格列表归一；`demo_data_missing`、`failed_workflows` 和 `storage_errors` 仍直接对 `release_readiness.get(...) or []` 做列表推导。
- 影响范围：Streamlit 发布就绪侧边栏、异常 API 响应或契约漂移时的前端诊断信号。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：前端展示层现在对 `demo_data_missing`、`failed_workflows`、`storage_errors` 也要求字符串列表；字段非列表或列表内有非法元素时显示 `invalid` blocker。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_release_readiness_display_state_blocks_malformed_demo_data_missing -q` 失败，`blockers` 实际为逐字符列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_release_readiness_display_state_blocks_malformed_demo_data_missing tests/test_frontend_api.py::test_release_readiness_display_state_blocks_malformed_config_warning_codes tests/test_frontend_api.py::test_release_readiness_display_state_rejects_inconsistent_ready_payload -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1139 passed`。
