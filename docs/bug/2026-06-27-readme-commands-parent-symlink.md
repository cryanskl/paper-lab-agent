# README command validator followed symlinked parent directory

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且 `README.md` 的父级路径是指向仓库外目录的 symlink。
- 实际结果：validator 会跟随 symlinked parent 读取仓库外 README；只要目标文档里的命令引用满足检查，校验返回成功。
- 期望结果：README 作为发布和本地运行说明的命令契约时，文件和父级目录都必须来自普通仓库文件树；遇到 symlinked parent 应返回 command doc issue。

## 原因

- 根因：`missing_command_targets_for_doc()` 只拒绝 README 文件本身是 symlink 或非普通文件，没有检查父级目录链。
- 影响范围：发布前 README 命令 gate 可能基于仓库边界外的说明文档，削弱当前 checkout 的可运行性证明。

## 修复

- 在 `scripts/validate_readme_commands.py` 中增加 command doc 路径父级链 symlink 检查。
- 当任一父级目录是 symlink 时，返回 `command doc parent is not a regular directory` issue，不再继续读取目标文档。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_readme_parent -q` 失败，当前实现返回空列表。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_readme_parent tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_readme tests/test_release_contracts.py::test_readme_commands_validator_accepts_current_readme tests/test_release_contracts.py::test_readme_commands_validator_runs_as_release_script -q` 通过，`4 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "readme_commands"` 通过，`11 passed, 259 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`835 passed`；`bash scripts/release_check.sh` 通过。
