# Docs link validator followed symlinked target parent

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_docs_links.py`，且 Markdown link 或 backtick reference 指向的目标文件父级目录是 symlink。
- 实际结果：validator 会跟随 symlinked target parent；只要目标文件存在且仍在仓库内，校验返回成功。
- 期望结果：文档链接 gate 应拒绝 symlinked target parent，确保 README、AGENTS 和 docs 下的文件引用都来自普通仓库文件树。

## 原因

- 根因：`broken_doc_links()` 只拒绝目标文件本身是 symlink 或非普通文件，没有检查目标父级目录链。
- 影响范围：发布前文档链接 gate 可能接受通过 symlinked parent 间接指向的 Markdown、SQL、Python、shell、YAML 或 example 文件。

## 修复

- 在 `scripts/validate_docs_links.py` 中对 Markdown link target 和 backtick reference target 增加父级链 symlink 检查。
- 当目标路径任一父级目录是 symlink 时，分别返回 `link target parent is not a regular directory` 或 `reference target parent is not a regular directory` issue。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_link_target_parent tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_backtick_reference_target_parent -q` 失败，两个场景当前实现都返回空列表。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_link_target_parent tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_link_target tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_backtick_reference_target_parent tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_backtick_reference_target -q` 通过，`4 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "docs_links"` 通过，`16 passed, 258 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`839 passed`；`bash scripts/release_check.sh` 通过。
