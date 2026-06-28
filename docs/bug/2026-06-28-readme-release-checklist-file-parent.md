# README command validator skipped release checklist when docs was a file

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且仓库中的 docs 路径被误建成普通文件。
- 实际结果：validator 只检查 `README.md`，静默跳过 docs/release-checklist.md，返回空 issues。
- 期望结果：validator 应报告 `docs/release-checklist.md: command doc parent is not a regular directory`，避免发布清单命令校验被路径错误绕过。

## 原因

`command_doc_paths()` 只有在 `docs/release-checklist.md` 本身 `exists()` 时才把它加入待检查文档列表。当 docs 是普通文件时，release checklist 完整路径不存在，后续 `missing_command_targets_for_doc()` 根本不会运行，也就没有机会输出父级路径诊断。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：当 release checklist 候选路径的任一父级已存在但不是目录时，也把该文档加入命令文档检查列表；文档入口先检查普通文件父级并返回 `command doc parent is not a regular directory`。
- 影响范围：只改变 docs 父级损坏时的错误报告；正常缺失 release checklist 仍保持不额外报错，已存在 release checklist、README 命令、curl 和 uvicorn 校验保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_file_release_checklist_parent -q` 失败，当前实现返回空 issues。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_file_release_checklist_parent tests/test_release_contracts.py::test_readme_commands_validator_checks_release_checklist_commands tests/test_release_contracts.py::test_readme_commands_validator_accepts_current_readme -q` 通过，`3 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "readme_commands"` 通过，`29 passed, 336 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1111 passed`。
