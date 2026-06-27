# README command validator accepted symlinked command targets

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且 `README.md` 或 `docs/release-checklist.md` 中引用的脚本命令目标是 symlink，或其父级目录是 symlink。
- 实际结果：validator 只检查命令目标是否存在；symlinked script target 会被当作有效命令目标，后续参数校验还可能执行仓库边界外的脚本 `--help`。
- 期望结果：文档里的本地命令目标必须是仓库内普通文件；目标本身或父级链为 symlink 时应报告错误。

## 原因

- 根因：`scripts/validate_readme_commands.py` 的 `missing_command_targets_for_doc()` 对 `command_targets()` 返回的脚本路径只做 `(repo / target).exists()` 检查，没有复用 command doc 源文件已有的普通文件/父级链约束。
- 影响范围：README 命令发布校验、release checklist 命令校验、交付文档中本地脚本入口可信度。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：命令目标存在后继续检查父级链和目标类型；如果父级链包含 symlink，报告 `command target parent is not a regular directory`；如果目标本身是 symlink 或非普通文件，报告 `command target is not a regular file`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_script_target -q` 失败，当前实现返回空 issue 列表。
- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_script_target_parent -q` 失败，当前实现返回空 issue 列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_script_target tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_script_target_parent tests/test_release_contracts.py -q -k "readme_commands"` 通过，`15 passed, 264 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`852 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `852 passed`。
