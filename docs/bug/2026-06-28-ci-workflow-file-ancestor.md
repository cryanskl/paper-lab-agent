# release hygiene reported missing CI workflow when ancestor was a file

## 现象

- 触发命令、接口或页面：`python scripts/validate_release_hygiene.py .gitignore` 或调用 `missing_required_ci_release_gate(repo)`，其中 `<repo>/.github` 已存在但被误建为普通文件。
- 实际结果：校验返回 `ci_workflow`，表现为 CI workflow 缺失。
- 期望结果：校验应返回 `ci_workflow_parent_not_regular_directory`，明确指出 workflow 父级路径不是目录。

## 原因

- 根因：`missing_required_ci_release_gate` 在检查 `.github/workflows/ci.yml` 的父级链之前先执行 `workflow_path.exists()`，当 `.github` 是普通文件时提前返回 `ci_workflow`。
- 影响范围：发布前 CI hygiene gate 遇到损坏的 `.github` 路径时，错误定位不准确，容易误判为单纯缺少 workflow 文件。

## 修复

- 修改文件：`scripts/validate_release_hygiene.py`、`tests/test_release_contracts.py`
- 关键行为：新增父级链普通文件检查，在 workflow missing 判断前拒绝已存在但不是目录的祖先路径，同时保留真正缺失 workflow 时的 `ci_workflow` 结果。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_rejects_file_ci_workflow_ancestor -q` -> `1 failed`
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_rejects_file_ci_workflow_ancestor tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_ci_workflow_ancestor tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_ci_workflow_parent tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_ci_workflow tests/test_release_contracts.py::test_release_hygiene_validator_reports_missing_ci_release_gate -q` -> `5 passed`
- 完整 gate：`bash scripts/release_check.sh` -> `1104 passed`
