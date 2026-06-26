# Bug doc validator accepted pending release gate evidence

## 现象

- 触发命令：`scripts/validate_bug_docs.py` 校验 `docs/bug/*.md`。
- 实际结果：bug 文档的验证章节如果仍写着 `完整 gate：待运行 ...`，validator 仍然返回通过。
- 期望结果：bug 文档不能带着未闭环的完整 gate 证据进入发布 gate；validator 应报告该文件存在 pending release gate evidence。

## 原因

- 根因：validator 只检查标题、必需章节、空章节和模板占位符，没有检查 `完整 gate` 行是否仍处于待运行状态。
- 影响范围：发布审计、bug 修复记录可信度、交接时对完整 gate 是否已执行的判断。

## 修复

- 修改文件：`scripts/validate_bug_docs.py`、`tests/test_release_contracts.py`。
- 关键行为：新增 pending release gate evidence 检查；当 `完整 gate` 行仍包含 `待运行` 时，bug 文档校验失败。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_reports_pending_release_gate_evidence -q` 修复前失败，`issues` 为空。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_reports_pending_release_gate_evidence -q` 通过；`.venv/bin/python -m pytest tests/test_release_contracts.py -k bug_doc_validator -q` 通过，`3 passed, 170 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`706 passed`。
