# README command validator accepted symlinked command docs

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且 `README.md` 是指向仓库外 Markdown 文件的 symlink。
- 实际结果：只要 symlink 目标文档中的命令引用有效，validator 会跟随 symlink 并返回成功。
- 期望结果：README 命令发布检查应拒绝 symlinked command doc，避免 release gate 使用仓库边界外的启动和发布命令说明。

## 原因

- 根因：README command validator 在读取命令文档前只检查 README 是否存在，没有拒绝 symlink 或非普通文件。
- 影响范围：README 和 release checklist 中的脚本目标、Python 参数、uvicorn target 和本地 curl route 检查的输入可信度。

## 修复

- 在 `scripts/validate_readme_commands.py` 的 command doc 入口增加普通文件检查。
- 当 README 或 release checklist 是 symlink 或非普通文件时，返回 `command doc is not a regular file` issue，不再继续读取目标内容。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_readme -q` 失败，当前实现返回空列表。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_symlinked_readme -q` 通过，`1 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "readme_commands"` 通过，`10 passed, 252 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`827 passed`；`bash scripts/release_check.sh` 通过。
