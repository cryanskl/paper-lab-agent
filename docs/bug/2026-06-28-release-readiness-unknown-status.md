# Release readiness ignored unknown workflow statuses

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status`，且某个工作流状态字段为 `NULL`，例如 `documents.parse_status=NULL`。
- 实际结果：`status_counts` 会正确汇总为 `document_parse.unknown=1`，但 `release_readiness.failed_workflows` 为空，`ready` 可能仍为 `true`。
- 期望结果：未知工作流状态必须阻断发布就绪，避免不可判定的解析、索引、翻译、化学抽取或复核状态被误判为可发布。

## 原因

- 根因：`failed_workflow_errors()` 只把 `failed` 和 `rejected` 纳入阻断状态，没有处理 `status_count()` 为 `NULL` 状态生成的 `unknown` 桶。
- 影响范围：系统状态发布门禁、`scripts/release_check.sh` 的 live health 判定，以及新机器或迁移后出现空状态字段时的发布风险识别。

## 修复

- 修改文件：`app/routers/system.py`、`docs/接口设计文档.md`、`tests/test_api.py`。
- 关键行为：`release_readiness.failed_workflows` 现在会把 `unknown` 状态与 `failed/rejected` 一起列为阻断项，例如 `document_parse.unknown=1`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_release_readiness_blocks_unknown_workflow_statuses -q` 失败，`failed_workflows` 实际为空。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_release_readiness_blocks_unknown_workflow_statuses tests/test_api.py::test_system_status_reports_workflow_status_counts tests/test_api.py::test_system_release_readiness_blocks_rejected_chemistry_workflows tests/test_api.py::test_system_status_reports_release_readiness tests/test_api.py::test_release_readiness_allows_offline_config_warnings -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1131 passed`。
