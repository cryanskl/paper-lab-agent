# Release artifact validator allowed duplicate preflight warning codes

## 现象

- 触发命令、接口或页面：`python scripts/validate_release_artifacts.py --artifact-dir out/release --compact`
- 实际结果：如果 `release-manifest.json` 的 `preflight_warning_codes` 重复列出同一个 warning code，且 `preflight_warning_count`、details 和 manifest checksum 已同步更新，validator 仍可能返回成功。
- 期望结果：validator 应拒绝重复 warning code，确保 release handoff 的 preflight 摘要不会被重复计数污染。

## 原因

- 根因：`scripts/validate_release_artifacts.py` 只检查 warning codes 是字符串列表、count 与列表长度一致、details code 与 codes 一致，没有检查 codes 是否唯一。
- 影响范围：人工编辑或生成器 bug 造成重复 warning code 时，artifact validator 可能无法发现 release manifest 摘要漂移。

## 修复

- 修改文件：`scripts/validate_release_artifacts.py`、`tests/test_release_contracts.py`
- 关键行为：`preflight_warning_codes` 中出现重复字符串时，返回 `release manifest preflight_warning_codes duplicate`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_duplicate_preflight_warning_codes -q` -> `1 failed`，validator 对重复 warning code manifest 返回 0。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_duplicate_preflight_warning_codes -q` -> `1 passed`
- 完整 gate：`bash scripts/release_check.sh` -> `1095 passed`
