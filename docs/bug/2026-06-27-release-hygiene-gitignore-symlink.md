# Release hygiene accepted symlinked gitignore

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_release_hygiene.py`，且 `.gitignore` 是指向仓库外文件的 symlink。
- 实际结果：只要 symlink 目标文件包含全部必需 ignore pattern，validator 会跟随 symlink 并返回成功。
- 期望结果：发布 hygiene gate 应拒绝 symlinked `.gitignore`，避免发布检查依赖仓库边界外的 ignore 规则文件。

## 原因

- 根因：release hygiene 入口直接读取 `.gitignore` 内容，没有先检查该路径是否为仓库内普通文件。
- 影响范围：发布前 ignore/secret/generated-artifact hygiene 检查；如果 `.gitignore` 被替换为 symlink，gate 的输入来源不再可信。

## 修复

- 在 `scripts/validate_release_hygiene.py` 入口先检查 `.gitignore` 路径。
- 当路径是 symlink 或不是普通文件时，返回非零并报告 `gitignore is not a regular file`，不再继续读取目标内容。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_gitignore -q` 失败，当前实现返回 `0`。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_rejects_symlinked_gitignore -q` 通过，`1 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "release_hygiene"` 通过，`16 passed, 241 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`822 passed`；`bash scripts/release_check.sh` 通过。
