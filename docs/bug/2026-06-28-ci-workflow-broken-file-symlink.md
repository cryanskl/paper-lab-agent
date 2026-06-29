# Release hygiene validator misreported broken CI workflow symlinks as missing

## 现象

- 触发命令、接口或页面：调用 `missing_required_ci_release_gate()` 或运行 `scripts/validate_release_hygiene.py`，且 `.github/workflows/ci.yml` 是断开的 symlink。
- 实际结果：validator 返回 `ci_workflow`。
- 期望结果：validator 应返回 `ci_workflow_not_regular_file`，把 CI workflow 文件路径类型错误和真正缺失 workflow 区分开。

## 原因

`missing_required_ci_release_gate()` 在 workflow 普通文件检查前先判断 `workflow_path.exists()`。broken symlink 的 `exists()` 为假，函数直接返回 `ci_workflow`，跳过了后续已有的 symlink / regular file 诊断。

## 修复

- 修改文件：`scripts/validate_release_hygiene.py`、`tests/test_release_contracts.py`。
- 关键行为：CI workflow 入口只在路径既不存在也不是 symlink 时返回 `ci_workflow`；broken symlink 会进入普通文件检查并报告 `ci_workflow_not_regular_file`。
- 影响范围：只改变断开的 `.github/workflows/ci.yml` symlink 错误分类；真正缺失 workflow、正常 workflow、普通 symlink workflow、父级异常和 unreadable workflow 行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_rejects_broken_symlinked_ci_workflow -q` 失败，当前实现返回 `ci_workflow`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_rejects_broken_symlinked_ci_workflow tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_ci_workflow tests/test_release_contracts.py::test_release_hygiene_validator_reports_unreadable_ci_workflow tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_ci_workflow_parent tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_ci_workflow_ancestor tests/test_release_contracts.py::test_release_hygiene_validator_requires_ci_release_gate -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1122 passed`。
