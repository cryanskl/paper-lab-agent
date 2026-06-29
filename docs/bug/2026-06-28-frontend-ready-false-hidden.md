# Frontend release display hid ready false without details

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `release_readiness`，其中 `ready=false`，但 `demo_data_missing`、`failed_workflows`、`config_warning_codes` 和 `storage_errors` 都为空列表。
- 实际结果：前端展示状态为不可发布，但 `blockers` 为空，页面没有可展示的发布阻断原因。
- 期望结果：当 API 明确返回 `ready=false` 且没有明细 blocker 时，前端应显示 `ready=false` 兜底 blocker，避免诊断信息缺失。

## 原因

- 根因：`app/frontend_api.py` 的 `release_readiness_display_state()` 只从明细分组展开 blockers；没有复用 `scripts/health_check.py` 中 `ready=false` 的兜底语义。
- 影响范围：Streamlit 发布就绪侧边栏、异常 API 响应或上游只返回聚合 ready 状态时的前端诊断信号。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：当前端没有任何明细 blocker 但 `release_readiness.ready` 不是 `true` 时，展示 `release state:` 分组和 `ready=false` blocker。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_release_readiness_display_state_surfaces_ready_false_without_details -q` 失败，`blockers` 实际为 `[]`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_release_readiness_display_state_surfaces_ready_false_without_details tests/test_frontend_api.py::test_release_readiness_display_state_surfaces_only_blocking_config_warnings tests/test_frontend_api.py::test_release_readiness_display_state_blocks_malformed_config_warning_codes tests/test_frontend_api.py::test_release_readiness_display_state_blocks_malformed_demo_data_missing tests/test_frontend_api.py::test_release_readiness_display_state_rejects_inconsistent_ready_payload -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1140 passed`。
