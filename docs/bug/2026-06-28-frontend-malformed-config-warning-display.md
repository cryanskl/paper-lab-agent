# Frontend release display ignored malformed config warning codes

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `release_readiness`，其中 `config_warning_codes` 不是列表而是字符串，例如 `"unsupported_vector_db_backend"`。
- 实际结果：前端展示函数按字符串逐字符迭代，无法命中 blocking config warning，可能显示 `ready=true`。
- 期望结果：malformed `config_warning_codes` 应作为不可发布状态显示，避免页面侧边栏误报发布就绪。

## 原因

- 根因：`app/frontend_api.py` 的 `release_readiness_display_state()` 直接对 `release_readiness.get("config_warning_codes") or []` 做列表推导；当字段是字符串时会逐字符处理。
- 影响范围：Streamlit 发布就绪侧边栏、异常 API 响应或契约漂移时的前端诊断信号。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：前端展示层现在要求 `config_warning_codes` 是字符串列表；字段非列表或列表内有非法元素时会输出 `config_warning_codes:invalid` blocker，并将 `ready` 置为 `false`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_release_readiness_display_state_blocks_malformed_config_warning_codes -q` 失败，页面展示状态实际为 `ready=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_release_readiness_display_state_blocks_malformed_config_warning_codes tests/test_frontend_api.py::test_release_readiness_display_state_surfaces_only_blocking_config_warnings tests/test_frontend_api.py::test_release_readiness_display_state_rejects_inconsistent_ready_payload -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1138 passed`。
