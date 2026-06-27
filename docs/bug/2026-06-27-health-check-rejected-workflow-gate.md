# Health check workflow gate ignored rejected statuses

## 现象

- 触发命令、接口或页面：`python scripts/health_check.py --require-no-failed-workflows`，且 `/api/v1/system/status` 的 `status_counts` 中存在 `document_chemistry.rejected=1` 或 `reaction_sets.rejected=1`。
- 实际结果：health check CLI 只检查 `failed` 状态，遇到 `rejected` 工作流仍返回 0。
- 期望结果：`rejected` 表示需要人工处理或重新抽取的工作流结果，应和 `failed` 一样阻断该部署前门禁。

## 原因

- 根因：`scripts/health_check.py` 的 `failed_workflow_errors()` 只汇总 `failed`，没有与 `/api/v1/system/status.release_readiness.failed_workflows` 的 `failed` + `rejected` 语义保持一致。
- 影响范围：发布前 CLI 检查、真实论文化学抽取无反应后的部署判断、README 中对健康检查门禁的说明。

## 修复

- 修改文件：`scripts/health_check.py`、`tests/test_api.py`、`README.md`。
- 关键行为：`--require-no-failed-workflows` 现在会在 `status_counts` 里发现 `failed` 或 `rejected` 正计数时返回非零，并输出对应阻断项。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_require_no_failed_workflows_fails_on_rejected_status_counts -q` 失败，当前实现返回 0。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_require_no_failed_workflows_fails_on_rejected_status_counts tests/test_api.py::test_health_check_require_no_failed_workflows_fails_on_failed_status_counts tests/test_api.py::test_system_release_readiness_blocks_rejected_chemistry_workflows -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "health_check"` 通过，`64 passed, 350 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`848 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `848 passed`。
