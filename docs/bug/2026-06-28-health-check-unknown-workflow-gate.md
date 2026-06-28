# Health check workflow gate ignored unknown statuses

## 现象

- 触发命令、接口或页面：`python scripts/health_check.py --require-no-failed-workflows`，且 `/api/v1/system/status` 的 `status_counts` 中存在 `document_parse.unknown=1`。
- 实际结果：health check CLI 只检查 `failed` 和 `rejected` 状态，遇到 `unknown` 工作流仍返回 0。
- 期望结果：`unknown` 表示无法判定的工作流状态，应和 `failed`、`rejected` 一样阻断该部署前门禁。

## 原因

- 根因：`scripts/health_check.py` 的 `failed_workflow_errors()` 没有与 `/api/v1/system/status.release_readiness.failed_workflows` 的 `failed` + `rejected` + `unknown` 语义保持一致。
- 影响范围：发布前 CLI 检查、`scripts/release_check.sh` 的 live health 判定，以及空白或 `NULL` 工作流状态被 API 汇总为 `unknown` 后的部署判断。

## 修复

- 修改文件：`scripts/health_check.py`、`tests/test_api.py`、`README.md`。
- 关键行为：`--require-no-failed-workflows` 现在会在 `status_counts` 里发现 `failed`、`rejected` 或 `unknown` 正计数时返回非零，并输出对应阻断项。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_require_no_failed_workflows_fails_on_unknown_status_counts -q` 失败，当前实现返回 0。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_require_no_failed_workflows_fails_on_unknown_status_counts tests/test_api.py::test_health_check_require_no_failed_workflows_fails_on_rejected_status_counts tests/test_api.py::test_health_check_require_no_failed_workflows_fails_on_failed_status_counts tests/test_api.py::test_system_release_readiness_blocks_unknown_workflow_statuses -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1133 passed`。
