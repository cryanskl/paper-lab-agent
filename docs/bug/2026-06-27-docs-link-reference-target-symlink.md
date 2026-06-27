# Docs link validator accepted symlinked reference targets

## 现象

- 触发命令、接口或页面：`python scripts/validate_docs_links.py` 或 `broken_doc_links()` 校验反引号文件引用，且文档中引用的脚本、CI workflow 或 env example 等文件是 symlink。
- 实际结果：validator 只通过 `target_exists()` 判断引用目标存在；该判断会跟随 symlink，导致 symlinked reference target 被当作有效目标接受。
- 期望结果：文档链接发布 gate 应拒绝 symlinked reference targets，避免仓库外运行文件被误判为仓库内发布依赖。

## 原因

- 根因：`scripts/validate_docs_links.py` 的反引号文件引用检查只调用 `target_exists()`，没有在解析目标路径后检查 `target_path.is_symlink()` 或普通文件类型。
- 影响范围：release docs link gate、发布前运行命令和文件引用完整性检查。

## 修复

- 修改文件：`scripts/validate_docs_links.py`、`tests/test_release_contracts.py`。
- 关键行为：反引号文件引用解析到目标后继续要求它不是 symlink 且是普通文件，否则返回 `reference target is not a regular file` issue。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_backtick_reference_target -q` 失败，当前实现返回空列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_backtick_reference_target tests/test_release_contracts.py::test_docs_links_validator_reports_missing_backtick_reference tests/test_release_contracts.py::test_docs_links_validator_reports_missing_backtick_runtime_file_reference tests/test_release_contracts.py::test_docs_links_validator_ignores_backtick_glob_patterns tests/test_release_contracts.py::test_docs_links_validator_accepts_current_docs tests/test_release_contracts.py::test_docs_links_validator_runs_as_release_script -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `819 passed`。
