# Bug doc validator misreported broken bug directory symlinks as missing

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_bug_docs.py`，且 `docs/bug` 目录路径是断开的 symlink。
- 实际结果：validator 返回 `docs/bug: missing`。
- 期望结果：validator 应返回 `docs/bug: bug directory is not a regular directory`，把 bug 记录目录路径类型错误和真正缺失目录区分开。

## 原因

`bug_doc_issues()` 在 `docs/bug` 目录类型检查前先判断 `bug_dir.exists()`。broken symlink 的 `exists()` 为假，函数直接返回 missing，跳过了后续已有的 symlink / directory 诊断。

## 修复

- 修改文件：`scripts/validate_bug_docs.py`、`tests/test_release_contracts.py`。
- 关键行为：`docs/bug` 入口只在路径既不存在也不是 symlink 时报告 missing；broken symlink 会进入目录类型检查并报告 `bug directory is not a regular directory`。
- 影响范围：只改变断开的 `docs/bug` symlink 错误分类；真正缺失 bug 目录、正常 bug 目录、普通 symlink bug 目录、父级异常和 README symlink 行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_rejects_broken_symlinked_bug_dir -q` 失败，当前实现返回 `docs/bug: missing`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_rejects_broken_symlinked_bug_dir tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_dir tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_parent tests/test_release_contracts.py::test_bug_doc_validator_rejects_file_bug_parent tests/test_release_contracts.py::test_bug_doc_validator_rejects_broken_symlinked_readme tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_doc -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1124 passed`。
