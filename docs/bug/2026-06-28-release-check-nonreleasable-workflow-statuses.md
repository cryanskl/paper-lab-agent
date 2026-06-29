# Release check smoke gate ignored non-releasable workflow statuses

## 现象

- 触发命令、接口或页面：`bash scripts/release_check.sh` 的 smoke payload 校验阶段，且 `status_counts` 中存在 `document_chemistry.rejected=1` 或 `document_parse.unknown=1`。
- 实际结果：release gate 的独立 smoke `status_counts` 兜底扫描只检查 `failed`，不会直接拦截 `rejected` 或 `unknown` 正计数。
- 期望结果：release gate 的 smoke 校验应与 `/api/v1/system/status.release_readiness.failed_workflows` 保持一致，把 `failed`、`rejected` 和 `unknown` 都作为不可发布工作流状态。

## 原因

- 根因：`scripts/release_check.sh` 内嵌的 smoke payload 校验仍使用旧的 `failed_statuses` 逻辑，只读取每个 workflow 计数字典里的 `failed`。
- 影响范围：发布前完整 gate 的防御层；当 `release_readiness` 和 `status_counts` 不一致时，`rejected` 或 `unknown` workflow backlog 可能不会被 release gate 的兜底状态扫描指出。

## 修复

- 修改文件：`scripts/release_check.sh`、`tests/test_release_contracts.py`、`docs/release-checklist.md`。
- 关键行为：release gate 的 smoke payload 校验现在扫描 `failed`、`rejected` 和 `unknown`，发现正计数时返回非零并输出 `smoke workflow statuses not releasable (...)`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_rejects_non_releasable_smoke_status_counts -q` 失败，当前脚本缺少 `blocking_statuses` 和 `failed/rejected/unknown` 阻断集合。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_rejects_non_releasable_smoke_status_counts tests/test_api.py::test_health_check_require_no_failed_workflows_fails_on_unknown_status_counts tests/test_api.py::test_system_release_readiness_blocks_unknown_workflow_statuses -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1133 passed`。
