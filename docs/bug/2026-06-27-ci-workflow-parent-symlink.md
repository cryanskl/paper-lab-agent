# Release hygiene followed symlinked CI workflow parent

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_release_hygiene.py`，且 `.github/workflows` 是指向仓库外目录的 symlink。
- 实际结果：只要 symlink 目标目录下的 workflow 文件包含有效 CI release gate 配置，validator 会跟随父目录 symlink 并返回成功。
- 期望结果：发布 hygiene 检查应拒绝 symlinked CI workflow 父目录，避免 GitHub Actions 发布 gate 契约来自仓库边界外。

## 原因

- 根因：上一阶段只拒绝 workflow 文件本身是 symlink，没有检查 workflow 文件的直接父目录。
- 影响范围：CI workflow 的来源边界；触发器、checkout、Python setup、requirements 安装、超时和 release gate 命令检查可能基于仓库外文件。

## 修复

- 在 `scripts/validate_release_hygiene.py` 的 CI workflow 检查入口增加直接父目录检查。
- 当 `.github/workflows` 是 symlink 或非目录时，返回 `ci_workflow_parent_not_regular_directory`，不再继续读取目标目录下的 workflow。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_ci_workflow_parent -q` 失败，当前实现返回空列表。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_ci_workflow_parent tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_ci_workflow -q` 通过，`2 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "release_hygiene"` 通过，`18 passed, 246 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`829 passed`；`bash scripts/release_check.sh` 通过。
