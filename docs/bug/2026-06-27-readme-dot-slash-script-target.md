# README command validator ignored dot-slash script targets

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且 README 或 release checklist 中使用 `./scripts/...` 形式记录本地脚本命令。
- 实际结果：validator 只识别 `scripts/...`，不会把 dot-slash 形式的 Python 或 shell 脚本纳入命令目标检查。
- 期望结果：`./scripts/...` 和 `scripts/...` 应走同一套存在性、仓库边界、symlink 和参数校验，避免常见 shell 写法绕过发布文档门禁。

## 原因

- 根因：`command_targets()` 只判断 token 是否 `startswith("scripts/")`；`python_script_option_refs()` 也只接受 `scripts/` 开头的 Python 脚本路径，没有先规范化开头的 `./`。
- 影响范围：README 命令发布校验、release checklist 命令校验、本地脚本命令目标可信度。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：解析本地脚本 token 时先去掉开头的 `./`；之后继续复用已有的缺失文件、仓库边界、symlink 和 `--help` 参数校验。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_reports_missing_dot_slash_script_target -q` 失败，当前实现返回空 issue 列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_reports_missing_dot_slash_script_target tests/test_release_contracts.py -q -k "readme_commands"` 通过，`19 passed, 264 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`857 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `857 passed`。
