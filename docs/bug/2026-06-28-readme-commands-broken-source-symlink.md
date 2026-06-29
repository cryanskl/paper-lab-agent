# README command validator misreported broken README symlinks as missing

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且 `README.md` 是断开的 symlink。
- 实际结果：validator 输出 `README.md: missing`。
- 期望结果：validator 应输出 `README.md: command doc is not a regular file`，把文档源路径类型错误和真正缺失 README 区分开。

## 原因

`missing_command_targets()` 在进入 `missing_command_targets_for_doc()` 前先判断 `readme_path.exists()`。broken symlink 的 `exists()` 为假，函数直接返回 missing，跳过了后续已有的 symlink / regular file 诊断。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：README 入口只在路径既不存在也不是 symlink 时返回 `README.md: missing`；broken symlink 会进入 command doc 普通文件检查。
- 影响范围：只改变断开的 README symlink 错误分类；真正缺失 README、正常 README、非 UTF-8 README、普通 symlink README 和后续命令校验保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_broken_symlinked_readme -q` 失败，当前实现输出 `README.md: missing`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_broken_symlinked_readme tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_readme tests/test_release_contracts.py::test_readme_commands_validator_reports_unreadable_readme tests/test_release_contracts.py::test_readme_commands_validator_accepts_current_readme -q` 通过，`4 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "readme_commands"` 通过，`31 passed, 339 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1116 passed`。
