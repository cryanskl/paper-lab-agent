# Docs link validator misreported file target parents as missing

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_docs_links.py`，且 Markdown link 指向的目标路径中间父级已经是普通文件，例如 `docs/schema.sql` 中的 `docs` 是文件。
- 实际结果：validator 输出 `missing link target docs/schema.sql`。
- 期望结果：validator 应输出 `link target parent is not a regular directory docs/schema.sql`，把路径结构错误和真正缺失目标区分开。

## 原因

`broken_doc_links()` 先调用 `resolve_target_path()`，而 `resolve_target_path()` 只返回已存在目标文件。目标父级是普通文件时，完整目标路径不存在，调用方直接进入 missing 分支，未检查候选目标路径父级链。

## 修复

- 修改文件：`scripts/validate_docs_links.py`、`tests/test_release_contracts.py`。
- 关键行为：新增候选目标路径父级检查；当目标不存在但候选路径任一父级是 symlink 或已存在的非目录时，在 missing 前返回 `link target parent is not a regular directory`。
- 影响范围：只改变不规则父级导致目标不存在时的错误分类；普通缺失链接、已存在链接、锚点校验和既有 symlink 父级拒绝行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_file_markdown_link_target_parent -q` 失败，当前实现输出 `missing link target docs/schema.sql`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_file_markdown_link_target_parent tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_markdown_link_target_parent tests/test_release_contracts.py::test_docs_links_validator_reports_missing_markdown_link -q` 通过，`3 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "docs_links"` 通过，`19 passed, 344 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1109 passed`。
