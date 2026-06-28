# Docs link validator crashed on unreadable source

## 现象

- 触发命令、接口或页面：运行 `python scripts/validate_docs_links.py` 或调用 `broken_doc_links(repo)`，且 `README.md`、`AGENTS.md`、`CLAUDE.md` 或 `docs/*.md` 中某个 Markdown source 不是 UTF-8 文本或读取阶段抛出 `OSError`。
- 实际结果：校验器在读取 Markdown source 时抛出底层异常，例如 `UnicodeDecodeError` traceback。
- 期望结果：docs link gate 应返回稳定 issue，指出具体 Markdown source 不可读，而不是中断整个 release gate。

## 原因

- 根因：`scripts/validate_docs_links.py` 的 `broken_doc_links()` 在确认 source 不是 symlink 且是普通文件后，直接调用 `path.read_text(encoding="utf-8")`；读取和解码错误没有转换为可报告 issue。
- 影响范围：文档链接校验、release gate、CI 文档 hygiene 检查。

## 修复

- 修改文件：`scripts/validate_docs_links.py`、`tests/test_release_contracts.py`。
- 关键行为：Markdown source regular-file 检查通过后，读取失败或解码失败时追加 `<source>: doc source unreadable` issue，并继续检查其他文档 source。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_reports_unreadable_markdown_source -q` 失败，函数抛出 `UnicodeDecodeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "docs_links_validator"` 通过，`17 passed, 284 deselected`；`.venv/bin/python -m py_compile scripts/validate_docs_links.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`908 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `908 passed`。
