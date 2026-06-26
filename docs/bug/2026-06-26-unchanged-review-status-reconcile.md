# Unchanged reaction reviews did not reconcile set status

## 现象

- 触发接口：`PUT /api/v1/reactions/{id}/verify`。
- 实际结果：当反应已经 `verified=1`，但所属 `reaction_sets.status` 因历史数据或迁移漂移仍为 `pending` 时，再次提交同值复核只新增审计日志，返回的反应集仍是 `pending`。
- 期望结果：同值复核也应根据当前反应复核状态重算 reaction set；当所有反应均已复核时，反应集应恢复为 `verified` 并更新 `verified_by` / `verified_at`。

## 原因

- 根因：`app/services/chemistry.py` 的 `verify_reaction` 在 `changed_updates` 为空时提前返回。
- 影响范围：历史漂移数据会出现 `export_ready=true` 但 `reaction_sets.status='pending'` 的不一致状态，影响状态统计、发布排障和前端复核判断。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：新增 reaction set 复核状态重算 helper；无论本次复核是否修改字段，都会根据未复核反应数量把 reaction set 校正为 `verified` 或 `pending`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_reaction_verify_reconciles_reaction_set_status_on_unchanged_review -q` 失败，返回 `status='pending'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_reaction_verify_reconciles_reaction_set_status_on_unchanged_review tests/test_api.py::test_reaction_verify_records_audit_for_unchanged_review tests/test_api.py::test_reaction_unverify_returns_reaction_set_to_pending tests/test_api.py::test_reaction_verify_updates_fields_and_records_audit -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`738 passed`。
