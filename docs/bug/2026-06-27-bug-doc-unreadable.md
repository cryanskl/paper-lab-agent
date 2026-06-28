# Bug doc validator crashed on unreadable bug record

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_bug_docs.py`，且 `docs/bug/*.md` 中存在非 UTF-8 或不可读取的 bug 记录文件。
- 实际结果：validator 在读取该文件时抛出 `UnicodeDecodeError` 或 `OSError`，release gate 以 traceback 形式失败。
- 期望结果：不可读取的 bug 记录应被报告为稳定 issue，校验器继续处理其它文件，不输出 traceback。

## 原因

- 根因：`bug_doc_issues()` 在确认 bug 文档是普通文件后直接调用 `path.read_text(encoding="utf-8")`，没有把读取和解码失败转换为校验问题。
- 影响范围：`docs/bug` 发布证据校验；坏文件会中断整个 bug-doc gate，而不是给出可修复的文件级错误。

## 修复

- 修改文件：`scripts/validate_bug_docs.py`、`tests/test_release_contracts.py`
- 关键行为：读取 bug 文档时捕获 `OSError` 和 `UnicodeDecodeError`，追加 `<path>: bug doc unreadable` issue 并跳过该文件后续内容检查。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_reports_unreadable_bug_doc -q` 失败，当前实现抛出 `UnicodeDecodeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_reports_unreadable_bug_doc -q` 通过，`1 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`913 passed`；`bash scripts/release_check.sh` 通过。
