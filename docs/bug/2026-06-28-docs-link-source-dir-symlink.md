# Docs link validator skipped empty symlinked docs directory

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_docs_links.py`，且仓库内 docs 路径是指向仓库外空目录的 symlink。
- 实际结果：validator 只检查 `README.md` 等顶层文档，未发现 docs 源目录不是普通目录，返回空 issues。
- 期望结果：validator 应报告 `docs: doc source directory is not a regular directory`，避免文档链接 gate 接受目录外的 docs 源边界。

## 原因

`doc_files()` 只把实际枚举到的 Markdown 文件加入检查列表。docs 是 symlink 且目标目录没有 Markdown 文件时，没有任何 docs 下的 source 文件进入 `broken_doc_links()` 的父级链检查，因此整个 docs 源目录形态被静默跳过。

## 修复

- 修改文件：`scripts/validate_docs_links.py`、`tests/test_release_contracts.py`。
- 关键行为：扫描 docs 源文件前记录 docs 目录本身是否为 symlink 或非目录；扫描完成后，如果没有更具体的 docs 相关 issue，则补充 `docs: doc source directory is not a regular directory`。
- 影响范围：只改变 docs 源目录自身损坏且没有更具体 docs issue 时的诊断；已有 source parent、link target parent、reference target parent 诊断保持优先。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_empty_docs_dir -q` 失败，当前实现返回空 issues。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_empty_docs_dir tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_link_target_parent tests/test_release_contracts.py::test_docs_links_validator_rejects_file_markdown_link_target_parent tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_source_parent -q` 通过，`4 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "docs_links"` 通过，`20 passed, 347 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1113 passed`。
