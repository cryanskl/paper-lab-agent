# README command validator skipped release checklist under symlinked docs

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且仓库内 docs 路径是指向仓库外目录的 symlink，同时目标目录里没有 release checklist。
- 实际结果：validator 只检查 `README.md`，静默跳过 `docs/release-checklist.md`，返回空 issues。
- 期望结果：validator 应报告 `docs/release-checklist.md: command doc parent is not a regular directory`，避免发布清单命令校验被 symlinked docs 路径绕过。

## 原因

`command_doc_paths()` 只有在 `docs/release-checklist.md` 本身 `exists()`，或其父级是普通文件时，才把它加入待检查文档列表。仓库内 docs 是 symlink 且目标 release checklist 不存在时，完整路径不存在，函数没有把该候选文档交给 `missing_command_targets_for_doc()` 做父级 symlink 诊断。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：当 release checklist 候选路径在 repo 内部命中 symlink 父级时，也加入命令文档检查列表；repo root 本身是 symlink 的既有诊断保持只报告 README 父级。
- 影响范围：只改变仓库内部 docs symlink 且 release checklist 不存在时的漏检；正常缺失 release checklist、repo root symlink、已存在 release checklist 和其他 README 命令校验保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_missing_release_checklist_parent -q` 失败，当前实现返回空 issues。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_missing_release_checklist_parent tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_readme_parent tests/test_release_contracts.py::test_readme_commands_validator_rejects_file_release_checklist_parent -q` 通过，`3 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "readme_commands"` 通过，`30 passed, 336 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1112 passed`。
