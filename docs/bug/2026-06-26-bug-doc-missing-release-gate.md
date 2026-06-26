# Bug doc validator accepted missing release gate evidence

## 现象

- 触发命令：`scripts/validate_bug_docs.py` 校验 `docs/bug/*.md`。
- 实际结果：bug 文档的验证章节如果完全缺少 `完整 gate` 行，validator 仍然返回通过。
- 期望结果：每份 bug 文档都必须包含完整 release gate 证据，且该行需要由 validator 继续检查是否已运行并包含 passed 数量。

## 原因

- 根因：validator 只在发现 `完整 gate` 行后检查是否 `待运行` 或缺少 `N passed`，没有要求该行必须存在。
- 影响范围：发布审计、历史 bug 修复记录可信度、交接时对 bug 修复是否跑过全量 gate 的判断。

## 修复

- 修改文件：`scripts/validate_bug_docs.py`、`tests/test_release_contracts.py`、旧 bug 记录。
- 关键行为：新增 missing release gate evidence 检查；当 bug 文档缺少 `完整 gate` 行时，bug 文档校验失败。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_reports_missing_release_gate_evidence -q` 修复前失败，`issues` 为空。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_reports_missing_release_gate_evidence -q` 通过；`.venv/bin/python -m pytest tests/test_release_contracts.py -k bug_doc_validator -q` 通过，`5 passed, 170 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
