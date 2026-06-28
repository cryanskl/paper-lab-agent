# Frontend release display crashed on malformed readiness object

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.release_readiness`，但该字段不是对象而是非空列表或字符串。
- 实际结果：`release_readiness_display_state()` 直接调用 `.get()`，前端会抛出 `AttributeError`，发布就绪诊断无法显示。
- 期望结果：malformed `release_readiness` 顶层对象应作为不可发布状态展示，而不是让侧边栏崩溃。

## 原因

- 根因：`streamlit_app.py` 只用 `status.get("release_readiness") or {}` 处理缺失或空值；非空 list/string 会原样传入 `app/frontend_api.py`，而 `release_readiness_display_state()` 假设输入一定是 dict。
- 影响范围：Streamlit 发布就绪侧边栏、异常 API 响应或接口契约漂移时的前端可用性。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：前端展示层现在先校验 `release_readiness` 顶层对象；非 dict 时返回 `release state:` 分组和 `release_readiness:invalid` blocker，并将 `ready` 置为 `false`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_release_readiness_display_state_blocks_malformed_readiness_object -q` 失败，错误为 `AttributeError: 'list' object has no attribute 'get'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_release_readiness_display_state_blocks_malformed_readiness_object tests/test_frontend_api.py::test_release_readiness_display_state_surfaces_ready_false_without_details tests/test_frontend_api.py::test_release_readiness_display_state_surfaces_only_blocking_config_warnings tests/test_frontend_api.py::test_release_readiness_display_state_blocks_malformed_config_warning_codes tests/test_frontend_api.py::test_release_readiness_display_state_blocks_malformed_demo_data_missing tests/test_frontend_api.py::test_release_readiness_display_state_rejects_inconsistent_ready_payload -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1141 passed`。
