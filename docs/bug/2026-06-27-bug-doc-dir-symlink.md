# Bug doc validator followed symlinked bug directories

## 现象

- 触发命令、接口或页面：`scripts/validate_bug_docs.py` 校验项目时，`docs/bug` 本身是指向目录外的 symlink。
- 实际结果：validator 跟随 symlink 进入目标目录，扫描并接受目标目录里的 bug 记录。
- 期望结果：`docs/bug` 必须是项目内的普通目录；symlinked bug 目录应被报告为无效输入，避免发布 gate 接受目录外的 bug 证据集合。

## 原因

- 根因：`bug_doc_issues()` 只检查 `docs/bug` 是否存在，没有在调用 `glob("*.md")` 前检查目录本身是否为 symlink 或普通目录。
- 影响范围：bug 记录发布校验、`scripts/release_check.sh` 中的 bug 文档 gate、发布证据目录边界。

## 修复

- 修改文件：`scripts/validate_bug_docs.py`、`tests/test_release_contracts.py`
- 关键行为：在扫描 bug 记录前拒绝 symlink 或非目录的 `docs/bug`，并返回 `docs/bug: bug directory is not a regular directory`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_dir -q` 失败，当前实现返回空 issue 列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "bug_doc_validator"` 通过，`7 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `778 passed`。
