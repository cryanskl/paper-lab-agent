# README command validator ignored inline uvicorn targets

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且 README 或 release checklist 正文中用反引号记录 `uvicorn` 启动命令。
- 实际结果：validator 只在 fenced shell 代码块里校验 `uvicorn` target；正文反引号中的 `uvicorn` 命令不会被采集，因此无效 app target 可绕过发布文档门禁。
- 期望结果：正文反引号和 fenced shell 代码块中的本地 `uvicorn` 命令应使用同一套 app target 校验。

## 原因

- 根因：`inline_command_lines()` 只采集 `LOCAL_COMMANDS` 中的命令或 `scripts/...` 命令，而 `LOCAL_COMMANDS` 没有包含 `uvicorn`。
- 影响范围：README 命令发布校验、release checklist 命令校验、正文内联启动命令的可信度。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：把 `uvicorn` 纳入 inline command 采集范围；采集后继续复用现有 `uvicorn` app target 校验，包括 missing 和 outside repository 检查。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_reports_missing_inline_uvicorn_app_target -q` 失败，当前实现返回空 issue 列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_reports_missing_inline_uvicorn_app_target tests/test_release_contracts.py -q -k "readme_commands"` 通过，`21 passed, 264 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`859 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `859 passed`。
