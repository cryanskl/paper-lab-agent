# Release readiness ignored blank workflow statuses

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status`，且某个工作流状态字段为空白字符串，例如 `documents.parse_status='   '`。
- 实际结果：`status_counts` 把空白字符串作为独立状态键返回，未归一为 `unknown`；`release_readiness.failed_workflows` 不会阻断该状态。
- 期望结果：空白工作流状态应与 `NULL` 一样按 `unknown` 统计，并阻断发布就绪。

## 原因

- 根因：`status_count()` 只使用 `COALESCE(<column>, 'unknown')` 处理 `NULL`，没有 `TRIM` 和 `NULLIF` 空白字符串。
- 影响范围：系统状态发布门禁、`scripts/release_check.sh` live health 判定，以及迁移或手工修复后出现空白状态字段时的发布风险识别。

## 修复

- 修改文件：`app/routers/system.py`、`docs/接口设计文档.md`、`tests/test_api.py`。
- 关键行为：状态汇总现在使用 `COALESCE(NULLIF(TRIM(status), ''), 'unknown')`，空白状态会进入 `unknown` 桶，并通过 `release_readiness.failed_workflows` 阻断发布。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_release_readiness_blocks_blank_workflow_statuses -q` 失败，`status_counts.document_parse` 没有 `unknown` 键。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_release_readiness_blocks_blank_workflow_statuses tests/test_api.py::test_system_release_readiness_blocks_unknown_workflow_statuses tests/test_api.py::test_system_status_reports_workflow_status_counts tests/test_api.py::test_system_release_readiness_blocks_rejected_chemistry_workflows tests/test_api.py::test_system_status_reports_release_readiness -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1132 passed`。
