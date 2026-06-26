# Rejected workflows were not release blockers

## 现象

- 触发接口：`GET /api/v1/system/status`。
- 实际结果：当 `documents.chemistry_status='rejected'` 且 `reaction_sets.status='rejected'` 时，`status_counts` 能看到 rejected 计数，但 `release_readiness.failed_workflows` 仍为空。
- 期望结果：`rejected` 表示需要人工处理或重新抽取的工作流结果，发布就绪门禁应把它列为阻断项，例如 `document_chemistry.rejected=1` 和 `reaction_sets.rejected=1`。

## 原因

- 根因：`app/routers/system.py` 的 `failed_workflow_errors` 只汇总 `failed` 状态。
- 影响范围：真实论文化学抽取无反应时会写入 `chemistry_status='rejected'` 和 `reaction_sets.status='rejected'`，此前可能被 `/system/status.release_readiness` 误判为无失败工作流。

## 修复

- 修改文件：`app/routers/system.py`、`tests/test_api.py`、`docs/接口设计文档.md`。
- 关键行为：`release_readiness.failed_workflows` 同时汇总 `failed` 和 `rejected` 状态；接口文档明确 `rejected` 是发布阻断状态。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_release_readiness_blocks_rejected_chemistry_workflows -q` 失败，`release_readiness.failed_workflows` 实际为空。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_release_readiness_blocks_rejected_chemistry_workflows tests/test_api.py::test_system_status_reports_workflow_status_counts tests/test_api.py::test_system_status_reports_release_readiness tests/test_api.py::test_system_status_contract_documents_operational_counts -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`737 passed`。
