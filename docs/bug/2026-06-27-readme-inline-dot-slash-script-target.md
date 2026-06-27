# README command validator ignored inline dot-slash script targets

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且 README 或 release checklist 正文中用反引号记录 dot-slash 形式的本地脚本命令。
- 实际结果：validator 的 inline command 采集只识别 `scripts/...` 或常见命令名，不会把 dot-slash 形式的脚本命令纳入命令目标检查。
- 期望结果：fenced bash 代码块和正文反引号中的本地脚本命令应使用同一套命令目标校验，不应因为多了 `./` 就绕过发布文档 gate。

## 原因

- 根因：`inline_command_lines()` 用首 token 判断候选命令时，只检查 `tokens[0].startswith("scripts/")`，没有先规范化开头的 `./`。
- 影响范围：README 命令发布校验、release checklist 命令校验、正文内联 runbook 命令的可信度。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：inline command 采集阶段对首 token 去掉开头的 `./` 后再判断是否为本地脚本命令；后续继续复用已有的缺失文件、仓库边界、symlink 和参数校验。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_reports_missing_inline_dot_slash_script_target -q` 失败，当前实现返回空 issue 列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_reports_missing_inline_dot_slash_script_target tests/test_release_contracts.py -q -k "readme_commands"` 通过，`20 passed, 264 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`858 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `858 passed`。
