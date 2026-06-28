# bug docs validator reported missing when parent was a file

## 现象

- 触发命令、接口或页面：`python scripts/validate_bug_docs.py <repo>`，其中 `<repo>/docs` 已存在但被误建为普通文件。
- 实际结果：校验返回 `docs/bug: missing`，没有指出 `docs/bug` 的父路径不是目录。
- 期望结果：校验应返回 `docs/bug: bug directory parent is not a regular directory`，明确定位父路径形态错误。

## 原因

- 根因：`bug_doc_issues` 在检查父级路径形态前先执行 `docs/bug.exists()`，当 `docs` 是普通文件时，`docs/bug` 被判断为不存在并提前返回 missing。
- 影响范围：发布 gate 中的 bug 文档校验遇到损坏的 `docs` 路径时，错误信息不够准确，影响发布前排障。

## 修复

- 修改文件：`scripts/validate_bug_docs.py`、`tests/test_release_contracts.py`
- 关键行为：在 `docs/bug` missing 判断前先拒绝父级 symlink 或普通文件，保留真正缺失目录时的 `docs/bug: missing` 语义。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_rejects_file_bug_parent -q` -> `1 failed`
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_rejects_file_bug_parent tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_dir tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_parent tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_readme -q` -> `4 passed`
- 完整 gate：`bash scripts/release_check.sh` -> `1103 passed`
