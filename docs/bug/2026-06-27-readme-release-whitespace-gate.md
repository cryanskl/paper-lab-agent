# README missed release whitespace gates

## 现象

- 触发命令、接口或页面：阅读 `README.md` 的 Verification 段落准备发布或演示前检查。
- 实际结果：README 说明 `bash scripts/release_check.sh` 会执行 strict doctor、启动脚本语法、编译和全量测试，但没有说明 release gate 也会执行 `git diff --check` 和 `git diff --cached --check`。
- 期望结果：README 应与 `scripts/release_check.sh` 和 `docs/release-checklist.md` 保持一致，明确入口发布命令会覆盖未暂存与已暂存 whitespace diff。

## 原因

- 根因：release gate 增加 staged/unstaged whitespace 检查后，README Verification 描述没有同步更新。
- 影响范围：新用户、发布前手动检查、demo handoff 文档入口。

## 修复

- 修改文件：`README.md`、`tests/test_release_contracts.py`
- 关键行为：README Verification 段落明确列出 `git diff --check` 和 `git diff --cached --check`，并用 release contract 测试固定。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_documents_release_check_whitespace_errors -q` 失败，`README.md` 缺少 `git diff --check` 和 `git diff --cached --check`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_documents_release_check_whitespace_errors tests/test_release_contracts.py::test_release_check_rejects_whitespace_errors -q` 通过，`2 passed`；`.venv/bin/python scripts/validate_docs_links.py` 通过；`git diff --check && git diff --cached --check` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`935 passed`；`bash scripts/release_check.sh` 通过，包含 `git diff --check`、`git diff --cached --check` 和 `.venv/bin/python -m pytest -q` 的 `935 passed`。
