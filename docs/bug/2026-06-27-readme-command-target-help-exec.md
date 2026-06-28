# README command validator executed unsafe command target help

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且 README 或 release checklist 中的 Python 脚本命令目标是 symlink，同时命令里带有选项参数。
- 实际结果：validator 会先报告命令目标不是普通文件，但随后仍进入 Python 脚本 option 校验，并对同一路径执行 `--help`。
- 期望结果：只要命令目标本身或父级链不可信，validator 可以报告问题，但不得为了参数校验执行这个脚本。

## 原因

- 根因：`missing_command_targets_for_doc()` 对 command target 做了普通文件检查，但后续 `missing_python_script_options_for_doc()` 重新遍历 Python option 引用时只判断路径是否存在，没有复用同一份安全检查。
- 影响范围：README 命令发布校验、release checklist 命令校验、本地发布门禁对文档中脚本入口的执行边界。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：执行 Python 脚本 `--help` 前先确认目标存在、父级链不含 symlink、目标本身不是 symlink 且是普通文件；不可信目标继续由 command target 校验报告，但 option 校验直接跳过，避免执行仓库边界外脚本。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_does_not_execute_symlinked_script_target_help -q` 失败，当前实现对同一个 symlinked target 追加了 `option --missing not found ... --help`，说明进入了 help 执行路径。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_does_not_execute_symlinked_script_target_help tests/test_release_contracts.py -q -k "readme_commands"` 通过，`15 passed, 264 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`853 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `853 passed`。
