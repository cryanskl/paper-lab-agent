# Docs link validator accepted absolute local link targets

## 现象

- 触发命令、接口或页面：`python scripts/validate_docs_links.py` 或 `broken_doc_links()` 校验 Markdown 链接，且文档链接到一个存在的绝对本地路径，例如本机 tmp 目录里的 outside Markdown 文件。
- 实际结果：validator 把存在的绝对本地文件当作有效链接目标，导致 release docs gate 通过。
- 期望结果：文档链接发布 gate 应拒绝指向仓库外的绝对本地路径，避免发布文档依赖当前机器上的私有文件。

## 原因

- 根因：`scripts/validate_docs_links.py` 的 `resolve_target_path()` 对 absolute target 只检查 `exists()`，`broken_doc_links()` 没有验证解析后的目标仍位于 repo 根目录内。
- 影响范围：release docs link gate、发布前文档完整性检查。

## 修复

- 修改文件：`scripts/validate_docs_links.py`、`tests/test_release_contracts.py`。
- 关键行为：Markdown link target 解析后必须仍在 repo 根目录内，否则返回 `link target escapes repository` issue。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_absolute_local_markdown_link_target -q` 失败，当前实现返回空列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_absolute_local_markdown_link_target tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_link_target tests/test_release_contracts.py::test_docs_links_validator_reports_missing_markdown_link tests/test_release_contracts.py::test_docs_links_validator_reports_missing_markdown_anchor tests/test_release_contracts.py::test_docs_links_validator_accepts_current_docs tests/test_release_contracts.py::test_docs_links_validator_runs_as_release_script -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `820 passed`。
