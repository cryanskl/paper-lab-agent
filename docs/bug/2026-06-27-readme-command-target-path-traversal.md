# README command validator accepted escaping command targets

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且 README 或 release checklist 中的 Python 命令目标使用 `..` 路径穿越逃出仓库。
- 实际结果：validator 把仓库外存在的脚本当成有效命令目标；如果命令带参数，还会对该仓库外脚本执行 `--help`。
- 期望结果：文档里的本地命令目标必须解析后仍位于仓库内；逃出仓库的目标应报告错误，并且不得执行 help 参数校验。

## 原因

- 根因：`missing_command_targets_for_doc()` 和 `safe_python_script_target()` 都只检查 `repo / target` 是否存在、是否普通文件或 symlink，没有验证 `resolve()` 后的真实路径仍在仓库内。
- 影响范围：README 命令发布校验、release checklist 命令校验、本地发布门禁对文档命令入口的仓库边界审计。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：新增仓库边界检查；命令目标存在后先确认真实路径仍在 repo 内，否则报告 `command target escapes repository`；Python script option help 校验也复用同一边界条件，不执行仓库外脚本。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_script_target_escaping_repo tests/test_release_contracts.py::test_readme_commands_validator_does_not_execute_escaping_script_target_help -q` 失败，一个用例返回空 issue，另一个进入仓库外脚本 `--help` 校验路径。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_script_target_escaping_repo tests/test_release_contracts.py::test_readme_commands_validator_does_not_execute_escaping_script_target_help tests/test_release_contracts.py -q -k "readme_commands"` 通过，`18 passed, 264 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`855 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `855 passed`。
