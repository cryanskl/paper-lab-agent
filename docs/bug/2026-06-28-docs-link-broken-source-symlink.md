# Docs link validator skipped broken source symlinks

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_docs_links.py`，且顶层文档源文件是断开的 symlink，例如 `README.md` 指向不存在的文件。
- 实际结果：validator 把该文档源从检查列表中跳过，返回空 issues。
- 期望结果：validator 应报告 `README.md: doc source is not a regular file`，避免断开的文档源 symlink 绕过发布前文档链接校验。

## 原因

`doc_files()` 只返回 `path.exists()` 为真的候选文档。broken symlink 的 `exists()` 为假，因此不会进入 `broken_doc_links()` 中已有的 `path.is_symlink()` / `not path.is_file()` 诊断分支。

## 修复

- 修改文件：`scripts/validate_docs_links.py`、`tests/test_release_contracts.py`。
- 关键行为：`doc_files()` 对顶层候选文档保留 `exists()` 或 `is_symlink()` 的路径，让 broken symlink 进入既有普通文件检查。
- 影响范围：只改变断开的文档源 symlink 漏检；正常缺失的可选顶层文档仍不额外报错，已有 symlink source、不可读 source 和正常文档链接行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_broken_symlinked_markdown_source -q` 失败，当前实现返回空 issues。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_broken_symlinked_markdown_source tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_source tests/test_release_contracts.py::test_docs_links_validator_reports_unreadable_markdown_source tests/test_release_contracts.py::test_docs_links_validator_accepts_current_docs -q` 通过，`4 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "docs_links"` 通过，`21 passed, 347 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1114 passed`。
