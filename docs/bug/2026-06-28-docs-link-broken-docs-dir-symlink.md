# Docs link validator skipped broken docs directory symlinks

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_docs_links.py`，且仓库内 docs 路径是断开的 symlink。
- 实际结果：validator 只检查顶层文档，未发现 docs 源目录不是普通目录，返回空 issues。
- 期望结果：validator 应报告 `docs: doc source directory is not a regular directory`，避免断开的 docs 源目录 symlink 绕过发布前文档链接校验。

## 原因

docs 目录级检查只在 `docs_dir.exists()` 为真时运行。broken symlink 的 `exists()` 为假，因此既不会进入 `doc_files()` 的 docs Markdown 枚举，也不会进入 docs 源目录形态诊断。

## 修复

- 修改文件：`scripts/validate_docs_links.py`、`tests/test_release_contracts.py`。
- 关键行为：docs 目录级检查同时接受 `docs_dir.exists()` 或 `docs_dir.is_symlink()`；断开的 docs symlink 会进入 `doc source directory is not a regular directory` 诊断。
- 影响范围：只改变 broken docs directory symlink 漏检；正常缺失 docs 目录、普通 docs 目录、已有 symlinked docs 目录和具体 docs issue 优先级保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_broken_symlinked_docs_dir -q` 失败，当前实现返回空 issues。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_broken_symlinked_docs_dir tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_empty_docs_dir tests/test_release_contracts.py::test_docs_links_validator_accepts_current_docs -q` 通过，`3 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "docs_links"` 通过，`22 passed, 347 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1115 passed`。
