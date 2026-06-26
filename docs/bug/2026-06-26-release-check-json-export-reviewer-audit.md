# Release gate 未暴露 JSON 导出复核人审计证据

## 现象

`scripts/smoke_check.py` 会在内部检查 JSON 导出的 `audit_log` 是否包含 `verified_by: smoke-check`，但 smoke summary 只返回 `verified_export_audit_entries` 数量。`scripts/release_check.sh` 因此只能证明存在审计项，无法从结构化输出证明 JSON 导出保留了本次人工复核人的身份。

## 原因

smoke 脚本把 reviewer identity 校验停留在局部断言里，没有把校验结果作为发布 gate 的 summary 字段输出；release gate 也没有期望字段覆盖这条证据。

## 修复

新增 `verified_export_has_smoke_check_audit` smoke summary 字段，并在 `scripts/release_check.sh` 的期望 payload 中要求该字段为 `True`。同时新增契约测试，防止后续删除这条 release gate 证据。

## 验证

先新增契约测试并确认红灯，再实现 smoke summary 与 release gate 断言。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_requires_json_export_reviewer_audit_metadata -q` 失败，缺少 `"verified_export_has_smoke_check_audit": True`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_requires_json_export_reviewer_audit_metadata -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -k "export or reaction_set" -q` 通过，`16 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`709 passed`。
