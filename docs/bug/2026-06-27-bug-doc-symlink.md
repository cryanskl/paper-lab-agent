# Bug doc validator followed symlinked bug records

## 现象

- 触发命令、接口或页面：`scripts/validate_bug_docs.py` 扫描 `docs/bug/*.md` 时遇到 symlink 类型的 bug 记录文件。
- 实际结果：validator 跟随 symlink 读取目标文件；如果目标内容满足模板，就不会报告问题。
- 期望结果：`docs/bug` 下的 bug 记录必须是普通文件；symlinked `.md` 应被报告为无效输入，避免发布 gate 接受目录外内容作为 bug 证据。

## 原因

- 根因：`bug_doc_issues()` 遍历 `bug_dir.glob("*.md")` 后直接调用 `path.read_text()`，没有在读取前检查 `path.is_symlink()` 或普通文件类型。
- 影响范围：bug 记录发布校验、`scripts/release_check.sh` 中的 bug 文档 gate、发布证据目录边界。

## 修复

- 修改文件：`scripts/validate_bug_docs.py`、`tests/test_release_contracts.py`
- 关键行为：读取 bug 记录前拒绝 symlink 或非普通文件，并报告 `bug doc is not a regular file`；正常 Markdown 内容校验规则保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_rejects_symlinked_bug_doc -q` 失败，当前实现返回空 issue 列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "bug_doc_validator"` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `777 passed`。
