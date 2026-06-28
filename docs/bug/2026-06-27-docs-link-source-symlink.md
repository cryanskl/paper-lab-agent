# Docs link validator accepted symlinked Markdown sources

## 现象

- 触发命令、接口或页面：`python scripts/validate_docs_links.py` 或 `broken_doc_links()` 校验文档链接，且 `README.md` 或 `docs/*.md` 是指向仓库外 Markdown 文件的 symlink。
- 实际结果：validator 直接调用 `Path.read_text()`，跟随 symlink 读取仓库外内容，并可能返回 `pass`。
- 期望结果：文档链接发布 gate 应拒绝 symlinked Markdown source，避免仓库外文档内容影响发布校验结果。

## 原因

- 根因：`scripts/validate_docs_links.py` 的 `broken_doc_links()` 在读取文档源文件前没有检查 `path.is_symlink()` 或普通文件类型。
- 影响范围：release docs link gate、发布前文档完整性检查。

## 修复

- 修改文件：`scripts/validate_docs_links.py`、`tests/test_release_contracts.py`。
- 关键行为：读取 Markdown source 前先拒绝 symlink 或非普通文件，返回 `doc source is not a regular file` issue，并跳过读取该文件。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_source -q` 失败，当前实现返回空列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_source tests/test_release_contracts.py::test_docs_links_validator_reports_missing_markdown_link tests/test_release_contracts.py::test_docs_links_validator_reports_missing_markdown_anchor tests/test_release_contracts.py::test_docs_links_validator_accepts_current_docs tests/test_release_contracts.py::test_docs_links_validator_runs_as_release_script -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `817 passed`。
