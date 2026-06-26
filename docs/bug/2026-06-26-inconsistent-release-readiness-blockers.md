# Release readiness blockers could be ignored

## 现象

`scripts/health_check.py` 消费 `/api/v1/system/status` 的 `release_readiness` 字段时，如果 API 返回 `ready: true`，但同时返回非空 `demo_data_missing`、`failed_workflows`、`config_warning_codes` 或 `storage_errors`，健康检查摘要会把 `release_ready` 判为 `true`。

这会让发布门禁在 API 响应出现内部不一致时错误放行。

## 原因

`release_readiness_blockers()` 先判断 `ready is True` 并直接返回空 blocker 列表，导致后续非空 blocker 字段完全不会被读取。

## 修复

调整 `release_readiness_blockers()` 的优先级：先汇总 blocker 列表；只在 blocker 为空时才信任 `ready: true`。

## 验证

RED：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_summary_rejects_inconsistent_api_release_readiness -q` 在修复前失败，`release_ready` 错误为 `true`。

GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_summary_rejects_inconsistent_api_release_readiness -q`

- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
