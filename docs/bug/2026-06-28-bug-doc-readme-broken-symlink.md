# Bug doc validator misreported broken README symlinks as missing

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_bug_docs.py`，且 `docs/bug/README.md` 是断开的 symlink。
- 实际结果：validator 返回 `docs/bug/README.md: missing`。
- 期望结果：validator 应返回 `docs/bug/README.md: bug docs README is not a regular file`，把 bug docs README 路径类型错误和真正缺失 README 区分开。

## 原因

`bug_doc_issues()` 在 README 普通文件检查前先判断 `readme_path.exists()`。broken symlink 的 `exists()` 为假，函数直接追加 missing issue，跳过了后续已有的 symlink / regular file 诊断。

## 修复

- 修改文件：`scripts/validate_bug_docs.py`、`tests/test_release_contracts.py`。
- 关键行为：bug docs README 入口只在路径既不存在也不是 symlink 时报告 missing；broken symlink 会进入普通文件检查并报告 `bug docs README is not a regular file`。
- 影响范围：只改变断开的 `docs/bug/README.md` symlink 错误分类；真正缺失 README、正常 README、普通 symlink README、bug 目录父级异常和单个 bug doc symlink 行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_rejects_broken_symlinked_readme -q` 失败，当前实现返回 `docs/bug/README.md: missing`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_rejects_broken_symlinked_readme tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_readme tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_dir tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_parent tests/test_release_contracts.py::test_bug_doc_validator_rejects_file_bug_parent tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_doc -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1123 passed`。
