# Docs link validator crashed on unreadable anchor target

## 现象

- 触发命令、接口或页面：运行 `python scripts/validate_docs_links.py` 或调用 `broken_doc_links(repo)`，且某个 Markdown 链接指向带 anchor 的本地 Markdown target，例如 `docs/guide.md#intro`，但该 target 文件不是 UTF-8 文本或读取阶段抛出 `OSError`。
- 实际结果：校验器在解析 target 文件 heading anchor 时抛出底层异常，例如 `UnicodeDecodeError` traceback。
- 期望结果：docs link gate 应返回稳定 issue，指出链接目标不可读，而不是中断整个 release gate。

## 原因

- 根因：`scripts/validate_docs_links.py` 的 `markdown_anchors()` 直接调用 `path.read_text(encoding="utf-8")`，而 `anchor_exists()` 没有把读取或解码错误转换为可报告 issue。
- 影响范围：文档链接 anchor 校验、release gate、CI 文档 hygiene 检查。

## 修复

- 修改文件：`scripts/validate_docs_links.py`、`tests/test_release_contracts.py`。
- 关键行为：Markdown anchor target 读取失败或解码失败时，`broken_doc_links()` 追加 `<source>: link target unreadable <target>#<fragment>` issue，并继续检查其他文档；target 文件本身作为 Markdown source 被扫描时仍会报告 `doc source unreadable`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_docs_links_validator_reports_unreadable_markdown_anchor_target -q` 失败，函数抛出 `UnicodeDecodeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "docs_links_validator"` 通过，`18 passed, 284 deselected`；`.venv/bin/python -m py_compile scripts/validate_docs_links.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`909 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `909 passed`。
