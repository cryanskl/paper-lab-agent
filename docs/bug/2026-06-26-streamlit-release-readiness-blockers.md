# Streamlit release readiness could ignore blockers

## 现象

Streamlit 侧边栏展示发布就绪状态时，只检查 `release_readiness.ready`。如果 API 响应里 `ready: true` 但 blocker 列表非空，页面仍会显示 `release ready`。

这会让前端发布状态与真实阻断项不一致。

## 原因

侧边栏在汇总 `demo_data_missing`、`failed_workflows`、`config_warning_codes` 和 `storage_errors` 之前，就用 `release_readiness.get("ready")` 决定成功状态。

## 修复

先汇总所有 blocker，再用 `release_ready = release_readiness.get("ready") is True and not blockers` 判断是否显示成功。

## 验证

RED：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_surfaces_release_readiness -q` 在修复前失败，缺少 blocker 优先判断。

GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_surfaces_release_readiness -q`

- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
