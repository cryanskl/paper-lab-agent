# Release check missed staged whitespace errors

## 现象

- 触发命令、接口或页面：运行 `bash scripts/release_check.sh`，且 whitespace 问题已经进入 Git index。
- 实际结果：release gate 只运行 `git diff --check`，不会检查 staged diff；如果工作区没有未暂存变化，已暂存的尾随空格或冲突标记问题可能漏过发布门禁。
- 期望结果：release gate 应同时运行 `git diff --check` 和 `git diff --cached --check`，覆盖未暂存与已暂存两类 diff whitespace 问题。

## 原因

- 根因：上一个 whitespace gate 只纳入了默认 `git diff --check`，该命令不覆盖已暂存到 index 的 diff。
- 影响范围：提交前发布门禁、GitHub 推送前验证，以及任何先 `git add` 再运行 release gate 的工作流。

## 修复

- 修改文件：`scripts/release_check.sh`、`tests/test_release_contracts.py`
- 关键行为：在 `scripts/release_check.sh` 中加入 `git diff --cached --check`，并用 release contract 测试固定 staged whitespace gate。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_rejects_whitespace_errors -q` 失败，`scripts/release_check.sh` 中缺少 `git diff --cached --check`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_rejects_whitespace_errors -q` 通过，`1 passed`；`bash -n scripts/release_check.sh` 通过；`git diff --check && git diff --cached --check` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`934 passed`；`bash scripts/release_check.sh` 通过，包含 `git diff --check`、`git diff --cached --check` 和 `.venv/bin/python -m pytest -q` 的 `934 passed`。
