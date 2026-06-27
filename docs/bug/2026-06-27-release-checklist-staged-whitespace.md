# Release checklist missed staged whitespace check

## 现象

- 触发命令、接口或页面：按 `docs/release-checklist.md` 的 Git Safety 步骤做发布前人工检查。
- 实际结果：checklist 记录了 `git diff --check`，但没有记录 `git diff --cached --check`。
- 期望结果：checklist 应与 `bash scripts/release_check.sh` 保持一致，明确检查未暂存与已暂存两类 whitespace diff。

## 原因

- 根因：发布 gate 增加 staged whitespace 检查后，人工 release checklist 没有同步更新。
- 影响范围：手动发布、demo handoff、以及先 `git add` 再按 checklist 做发布前检查的流程。

## 修复

- 修改文件：`docs/release-checklist.md`、`tests/test_release_contracts.py`
- 关键行为：Git Safety 命令块加入 `git diff --cached --check`，并说明两个 diff checks 分别覆盖 unstaged 与 staged whitespace 或 conflict-marker errors。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_checklist_documents_git_safety_checks -q` 失败，`docs/release-checklist.md` 缺少 `git diff --cached --check`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_checklist_documents_git_safety_checks -q` 通过，`1 passed`；`.venv/bin/python scripts/validate_docs_links.py` 通过；`git diff --check && git diff --cached --check` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`934 passed`；`bash scripts/release_check.sh` 通过，包含 `git diff --check`、`git diff --cached --check` 和 `.venv/bin/python -m pytest -q` 的 `934 passed`。
