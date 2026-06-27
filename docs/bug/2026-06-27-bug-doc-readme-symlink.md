# Bug doc validator accepted symlinked README

## 现象

- 触发命令、接口或页面：`scripts/validate_bug_docs.py` 校验 `docs/bug` 时，`docs/bug/README.md` 是指向目录外文件的 symlink。
- 实际结果：validator 只检查 README 是否存在，因此接受了 symlinked README。
- 期望结果：`docs/bug/README.md` 必须是普通文件；symlinked README 应被报告为无效输入，避免发布 gate 接受目录外的 bug 记录约定文件。

## 原因

- 根因：`bug_doc_issues()` 对 `docs/bug/README.md` 只调用 `exists()`，没有检查 `is_symlink()` 或普通文件类型。
- 影响范围：bug 记录发布校验、`scripts/release_check.sh` 中的 bug 文档 gate、发布证据目录约定文件边界。

## 修复

- 修改文件：`scripts/validate_bug_docs.py`、`tests/test_release_contracts.py`
- 关键行为：README 存在时继续要求它不是 symlink 且是普通文件，否则报告 `bug docs README is not a regular file`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_readme -q` 失败，当前实现返回空 issue 列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "bug_doc_validator"` 通过，`8 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `779 passed`。
