# Release hygiene accepted symlinked CI workflow

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_release_hygiene.py`，且 `.github/workflows/ci.yml` 是指向仓库外 workflow 文件的 symlink。
- 实际结果：只要 symlink 目标包含有效 CI release gate 配置，validator 会跟随 symlink 并返回成功。
- 期望结果：发布 hygiene 检查应拒绝 symlinked CI workflow，避免 GitHub Actions 发布 gate 契约来自仓库边界外。

## 原因

- 根因：`missing_required_ci_release_gate()` 在读取 workflow 文本前只检查路径是否存在，没有拒绝 symlink 或非普通文件。
- 影响范围：CI 触发器、checkout、Python setup、requirements 安装、超时和 release gate 命令检查的输入可信度。

## 修复

- 在 `scripts/validate_release_hygiene.py` 的 CI workflow 检查入口增加普通文件检查。
- 当 `.github/workflows/ci.yml` 是 symlink 或非普通文件时，返回 `ci_workflow_not_regular_file`，不再继续读取目标内容。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_ci_workflow -q` 失败，当前实现返回空列表。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_ci_workflow -q` 通过，`1 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "release_hygiene"` 通过，`17 passed, 246 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`828 passed`；`bash scripts/release_check.sh` 通过。
