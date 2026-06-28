# README command validator misreported file target parents as missing

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且 README 命令引用的脚本路径中间父级已经是普通文件，例如 scripts/tool.py 中的 scripts 是文件。
- 实际结果：validator 输出 `README.md: command target missing: scripts/tool.py`。
- 期望结果：validator 应输出 `README.md: command target parent is not a regular directory: scripts/tool.py`，把路径结构错误和真正缺失脚本区分开。

## 原因

`missing_command_targets_for_doc()` 先判断 `target_path.exists()`。当目标路径中间父级是普通文件时，完整目标路径不存在，函数直接进入 missing 分支，没有检查父级链是否存在非目录路径组件。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：新增普通文件父级检查；当命令目标不存在但候选路径任一父级已存在且不是目录时，在 missing 前返回 `command target parent is not a regular directory`。
- 影响范围：只改变不规则父级导致目标不存在时的错误分类；普通缺失脚本、symlink 父级、symlink 目标和现有命令解析行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_file_script_target_parent -q` 失败，当前实现输出 `command target missing: scripts/tool.py`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_file_script_target_parent tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_script_target_parent tests/test_release_contracts.py::test_readme_commands_validator_reports_missing_script_target -q` 通过，`3 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "readme_commands"` 通过，`28 passed, 336 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1110 passed`。
