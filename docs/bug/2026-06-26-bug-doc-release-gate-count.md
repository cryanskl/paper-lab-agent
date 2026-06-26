# Bug doc validator accepted release gate evidence without passed count

## 现象

- 触发命令：`scripts/validate_bug_docs.py` 校验 `docs/bug/*.md`。
- 实际结果：bug 文档的验证章节如果只写 `完整 gate：bash scripts/release_check.sh` 这类命令，没有记录 `N passed` 结果，validator 仍然返回通过。
- 期望结果：完整 gate 证据必须包含实际通过数量，例如 `707 passed`，否则发布审计无法确认全量 gate 是否真的执行并通过。

## 原因

- 根因：validator 只检查 `完整 gate` 是否还处于 `待运行` 状态，没有检查该行是否包含可验证的 passed 数量。
- 影响范围：发布审计、历史 bug 修复记录可信度、交接时对完整 release gate 覆盖范围的判断。

## 修复

- 修改文件：`scripts/validate_bug_docs.py`、`tests/test_release_contracts.py`、旧 bug 记录。
- 关键行为：新增 incomplete release gate evidence 检查；当 `完整 gate` 行缺少 `N passed` 结果时，bug 文档校验失败。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_reports_release_gate_without_passed_count -q` 修复前失败，`issues` 为空。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_reports_release_gate_without_passed_count -q` 通过；`.venv/bin/python -m pytest tests/test_release_contracts.py -k bug_doc_validator -q` 通过，`4 passed, 170 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`707 passed`。
