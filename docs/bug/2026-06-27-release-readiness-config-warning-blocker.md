# Release readiness blocked offline config warnings

## 现象

- 触发命令、接口或页面：默认离线配置下调用 `GET /api/v1/system/status` 或 `python scripts/health_check.py --require-release-ready`。
- 实际结果：缺少 `OPENALEX_MAILTO`、`UNPAYWALL_EMAIL` 或 `LLM_API_KEY` 时，`release_readiness.ready=false`，`health_check` 把 `config_warning_codes:*` 当成 release blocker。
- 期望结果：这些外部能力缺失只作为 `config_warnings` / `config_warning_codes` 暴露，不阻断默认离线模式的 release readiness；需要强制外部能力配置时继续使用 `--require-no-config-warnings`。

## 原因

- 根因：`release_readiness_status()` 和 `health_check.release_readiness_blockers()` 都把 `config_warning_codes` 纳入默认发布就绪阻断集合，和 P0 成品化路线里的“配置校验报告但不阻断本地离线模式”相冲突。

## 修复

- 关键行为：`release_readiness.ready` 只由 demo data、失败/拒绝工作流和存储错误决定；`config_warning_codes` 继续保留在响应和 summary 中，并通过 `config_ready=false` 或 `--require-no-config-warnings` 单独表达。
- 影响范围：默认离线 release readiness 允许缺少可选外部配置；正式演示或部署需要外部能力时，仍可用 `python scripts/health_check.py --require-no-config-warnings` 强制失败。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_release_readiness_allows_offline_config_warnings tests/test_api.py::test_health_check_require_release_ready_runs_combined_gates tests/test_api.py::test_health_check_require_release_ready_prefers_api_release_readiness tests/test_api.py::test_health_check_summary_rejects_inconsistent_api_release_readiness -q` 失败，当前实现把 `config_warning_codes` 当作 release blocker。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_release_readiness_allows_offline_config_warnings tests/test_api.py::test_health_check_require_release_ready_runs_combined_gates tests/test_api.py::test_health_check_require_release_ready_prefers_api_release_readiness tests/test_api.py::test_health_check_summary_rejects_inconsistent_api_release_readiness -q` 通过，`4 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_api.py -q -k "release_readiness or require_release_ready or config_warning or smoke_check_script_outputs_json or smoke_check_covers"` 通过，`18 passed, 380 deselected`。
- 全量验证：`.venv/bin/python -m pytest -q` 通过，`792 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `792 passed`。
