# Docs link validator accepted symlinked link targets

## 现象

- 触发命令、接口或页面：`python scripts/validate_docs_links.py` 或 `broken_doc_links()` 校验文档链接，且 Markdown 文档链接到 symlinked 文件，例如 `docs/schema.sql` 指向仓库外 SQL 文件。
- 实际结果：validator 使用 `Path.exists()` 解析链接目标；该判断会跟随 symlink，导致 symlinked link target 被当作有效目标接受。
- 期望结果：文档链接发布 gate 应拒绝 symlinked link targets，避免仓库外文件被误判为仓库内发布文档依赖。

## 原因

- 根因：`scripts/validate_docs_links.py` 的 `broken_doc_links()` 在解析 Markdown link target 后，没有检查 `target_path.is_symlink()` 或普通文件类型。
- 影响范围：release docs link gate、发布前文档完整性检查。

## 修复

- 修改文件：`scripts/validate_docs_links.py`、`tests/test_release_contracts.py`。
- 关键行为：Markdown link target 存在后继续要求它不是 symlink 且是普通文件，否则返回 `link target is not a regular file` issue，并跳过 anchor 检查。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_link_target -q` 失败，当前实现返回空列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_link_target tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_source tests/test_release_contracts.py::test_docs_links_validator_reports_missing_markdown_link tests/test_release_contracts.py::test_docs_links_validator_reports_missing_markdown_anchor tests/test_release_contracts.py::test_docs_links_validator_accepts_current_docs tests/test_release_contracts.py::test_docs_links_validator_runs_as_release_script -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `818 passed`。
