# Bug docs validator followed symlinked parent directory

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_bug_docs.py`，且 `docs/bug` 的父级路径是指向仓库外目录的 symlink。
- 实际结果：validator 会跟随 symlinked parent 读取仓库外 bug 文档目录；只要目标目录里的文档满足格式检查，校验返回成功。
- 期望结果：`docs/bug` 作为 bug 记录证据目录时，目录和父级目录都必须来自普通仓库文件树；遇到 symlinked parent 应返回非零。

## 原因

- 根因：`bug_doc_issues()` 只拒绝 `docs/bug` 本身是 symlink 或非普通目录，没有检查父级目录链。
- 影响范围：发布前 bug 记录 gate 可能基于仓库边界外的文档内容，削弱“bug 分开记录”的可审计性。

## 修复

- 在 `scripts/validate_bug_docs.py` 中增加 `docs/bug` 路径父级链 symlink 检查。
- 当任一父级目录是 symlink 时，返回 `bug directory parent is not a regular directory` issue，不再继续读取目标目录。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_parent -q` 失败，当前实现返回空列表。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_parent tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_dir tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_doc tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_readme -q` 通过，`4 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "bug_doc"` 通过，`9 passed, 262 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`836 passed`；`bash scripts/release_check.sh` 通过。
