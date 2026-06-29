# Release artifact validator missed preflight warning count drift

## 现象

- 触发命令、接口或页面：`python scripts/validate_release_artifacts.py --artifact-dir out/release --compact`
- 实际结果：如果 `release-manifest.json` 的 `preflight_warning_count` 与 `preflight_warning_codes` 数量不一致，但 manifest checksum 已同步更新，validator 仍可能返回成功。
- 期望结果：validator 应拒绝 warning count 与 warning codes/details 不一致的 handoff manifest，避免交接报告里的 preflight 摘要漂移。

## 原因

- 根因：`scripts/validate_release_artifacts.py` 只校验 `preflight_warning_count` 是整数、`preflight_warning_codes` 是字符串列表、details code 与 codes 一致，没有校验 count 与 codes 数量一致。
- 影响范围：人工编辑或生成器 bug 导致 manifest preflight summary 漂移时，单独运行 artifact validator 可能无法发现。

## 修复

- 修改文件：`scripts/validate_release_artifacts.py`、`tests/test_release_contracts.py`
- 关键行为：当 `preflight_warning_codes` 有效时，`preflight_warning_count` 必须等于 codes 数量，否则返回 `release manifest preflight_warning_count mismatch`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_preflight_warning_count_drift -q` -> `1 failed`，validator 对自洽 checksum 但 count 漂移的 manifest 返回 0。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_preflight_warning_count_drift -q` -> `1 passed`
- 完整 gate：`bash scripts/release_check.sh` -> `1094 passed`
