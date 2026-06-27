# Docs link validator followed symlinked source parent

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_docs_links.py`，且 Markdown 文档源文件的父级目录是指向仓库外目录的 symlink。
- 实际结果：validator 会跟随 symlinked parent 读取仓库外 Markdown 文档；只要目标文档链接合法，校验返回成功。
- 期望结果：文档链接 gate 应只验证当前仓库普通文件树中的文档源；遇到 symlinked source parent 应返回非零。

## 原因

- 根因：`broken_doc_links()` 只拒绝 Markdown 源文件本身是 symlink 或非普通文件，没有检查父级目录链。
- 影响范围：发布前文档链接 gate 可能基于仓库边界外的 Markdown 内容，削弱 README、AGENTS、docs 下文档的可审计性。

## 修复

- 在 `scripts/validate_docs_links.py` 中增加文档源路径父级链 symlink 检查。
- 当任一父级目录是 symlink 时，返回 `doc source parent is not a regular directory` issue，不再继续读取目标文档。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_source_parent -q` 失败，当前实现返回空列表。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_source_parent tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_source tests/test_release_contracts.py::test_docs_links_validator_accepts_current_docs tests/test_release_contracts.py::test_docs_links_validator_runs_as_release_script -q` 通过，`4 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "docs_links"` 通过，`14 passed, 258 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`837 passed`；`bash scripts/release_check.sh` 通过。
