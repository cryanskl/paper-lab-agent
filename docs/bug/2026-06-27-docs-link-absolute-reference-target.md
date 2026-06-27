# Docs link validator accepted absolute local reference targets

## 现象

- 触发命令、接口或页面：运行 docs link validator，且文档中的反引号文件引用指向一个存在的仓库外绝对本地脚本路径。
- 实际结果：validator 把这个存在的本地文件当作有效引用目标，导致 release docs gate 通过。
- 期望结果：文档链接发布 gate 应拒绝指向仓库外的绝对本地引用目标，避免发布文档依赖当前机器上的私有运行文件。

## 原因

- 根因：反引号文件引用分支解析目标后只检查 missing 和普通文件类型，没有复用 Markdown link target 的 repo 边界检查。
- 影响范围：文档里使用反引号引用本机绝对路径，且该文件真实存在时，validator 会漏报。

## 修复

- 为反引号文件引用补充 repo 边界检查。
- 当解析后的目标不在当前仓库内时，返回 `reference target escapes repository`，并跳过后续普通文件检查。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_absolute_local_backtick_reference_target -q` 失败，当前实现返回空列表。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_rejects_absolute_local_backtick_reference_target tests/test_release_contracts.py::test_docs_links_validator_rejects_symlinked_backtick_reference_target tests/test_release_contracts.py::test_docs_links_validator_reports_missing_backtick_reference tests/test_release_contracts.py::test_docs_links_validator_reports_missing_backtick_runtime_file_reference tests/test_release_contracts.py::test_docs_links_validator_accepts_current_docs tests/test_release_contracts.py::test_docs_links_validator_runs_as_release_script -q` 通过，`6 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`821 passed`；`bash scripts/release_check.sh` 通过。
