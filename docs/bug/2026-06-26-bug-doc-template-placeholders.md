# Bug doc validator accepted template leftovers

## 现象

`scripts/validate_bug_docs.py` 会接受从 `docs/bug/README.md` 复制后未填写完整的 bug 文档。只要四个必需章节存在且正文非空，类似只有模板标签、没有实际证据的记录也会通过发布 gate。

## 原因

validator 只检查标题、必需章节和空章节，没有检查模板中的证据标签是否仍然保持未填写状态。

## 修复

新增 `TEMPLATE_PLACEHOLDER_LABELS` 和 `unresolved_template_placeholders`，检测未填写的模板标签行。命中时返回 `unresolved template placeholders` 错误，让 `scripts/validate_bug_docs.py` 在 release gate 中失败。

## 验证

新增临时 repo 测试覆盖模板残留场景，并确认当前 `docs/bug` 目录仍通过校验：

```bash
python -m pytest tests/test_release_contracts.py::test_bug_doc_validator_reports_missing_title tests/test_release_contracts.py::test_bug_doc_validator_reports_unresolved_template_placeholders -q
python scripts/validate_bug_docs.py
```
