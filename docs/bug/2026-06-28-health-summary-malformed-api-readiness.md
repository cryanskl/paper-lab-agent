# Health summary ignored malformed API release readiness lists

## 现象

- 触发命令、接口或页面：`python scripts/health_check.py --summary-only --compact` 消费 `/api/v1/system/status`，响应中 `release_readiness.ready=true`，但 `release_readiness.failed_workflows` 不是列表。
- 实际结果：health summary 把 malformed `failed_workflows` 静默归一为空列表，可能输出 `release_ready=true` 和 `workflows_ok=true`。
- 期望结果：API 聚合的发布就绪列表字段形状异常时，summary 应标记为不可发布，避免快速检查误判。

## 原因

- 根因：`scripts/health_check.py` 的 `api_release_readiness()` 使用 `list_values()` 解析 `release_readiness` 列表字段；非列表字段会直接返回 `[]`，丢失异常信号。
- 影响范围：发布前 compact summary、`--require-release-ready` 错误定位前的 stdout 摘要、异常 API 响应的诊断信号。

## 修复

- 修改文件：`scripts/health_check.py`、`tests/test_api.py`。
- 关键行为：API `release_readiness.demo_data_missing`、`failed_workflows` 或 `storage_errors` 非列表时，summary 会加入 `invalid` blocker，例如 `failed_workflows:invalid`，并输出 `release_ready=false`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_summary_blocks_malformed_api_release_readiness_lists -q` 失败，summary 实际为 `release_ready=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_summary_blocks_malformed_api_release_readiness_lists tests/test_api.py::test_health_check_summary_prefers_api_release_readiness tests/test_api.py::test_health_check_summary_rejects_inconsistent_api_release_readiness -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1135 passed`。
