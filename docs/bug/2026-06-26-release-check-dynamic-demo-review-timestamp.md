# Release gate compares dynamic demo reviewer timestamps

## 现象

`bash scripts/release_check.sh` 在 `prepare_demo_data --summary-only` 校验阶段失败，错误为：

`release_check failed: prepare_demo_data --summary-only output does not match payload.summary`

## 原因

`scripts/release_check.sh` 会分别运行 full payload、`--summary-only` stdout 和 `--summary-only --output` 三条 demo preparation 路径，并把后两者与 full payload 的 `summary` 做全量相等比较。新增 `reaction_set_verified_at` 后，该字段来自独立 demo preparation run，时间戳天然可能不同，全量相等比较不再是稳定契约。

## 修复

改为比较 demo summary 的稳定字段，排除动态的 `reaction_set_verified_at`；同时单独校验每条 summary 的 `reaction_set_verified_by` 必须是 `prepare-demo-data`，且 `reaction_set_verified_at` 必须是可解析的 ISO8601 时间戳。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_validates_prepare_demo_data_output_artifact -q` 失败，缺少稳定字段比较和 reviewer timestamp 校验。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_validates_prepare_demo_data_output_artifact -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_requires_demo_reviewer_timestamp -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`741 passed`。
