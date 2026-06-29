# Health summary fallback ignored malformed workflow counts

## 现象

- 触发命令、接口或页面：`python scripts/health_check.py --summary-only --compact` 消费旧版或异常 `/api/v1/system/status` 响应，响应没有 `release_readiness`，且 `status_counts.document_parse` 不是对象。
- 实际结果：summary fallback 会跳过该 workflow 计数字段，可能输出 `release_ready=true`、`workflows_ok=true`。
- 期望结果：malformed workflow count 表示发布状态不可判定，应在 summary 中作为 workflow blocker 暴露，避免快速检查误判可发布。

## 原因

- 根因：`scripts/health_check.py` 的 `failed_workflow_errors()` 遇到非对象 workflow count 时直接 `continue`，而 `health_summary()` 在缺少 API 聚合的 `release_readiness` 时依赖该函数推断 workflow readiness。
- 影响范围：发布前 compact summary、旧 API fallback 场景、异常状态响应的快速诊断信号。

## 修复

- 修改文件：`scripts/health_check.py`、`tests/test_api.py`。
- 关键行为：非对象 workflow count 现在会以 workflow 名称进入 `failed_workflows`，summary 输出 `release_ready=false` 和 `failed_workflows:<workflow>` blocker。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_summary_blocks_malformed_fallback_workflow_counts -q` 失败，summary 实际为 `release_ready=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_summary_blocks_malformed_fallback_workflow_counts tests/test_api.py::test_health_check_summary_only_reports_release_ready_when_gates_are_clean tests/test_api.py::test_health_check_require_no_failed_workflows_fails_on_unknown_status_counts -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1134 passed`。
