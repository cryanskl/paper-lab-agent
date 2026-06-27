# Release check missed whitespace errors

## 现象

- 触发命令、接口或页面：运行 `bash scripts/release_check.sh`。
- 实际结果：release gate 会执行语法、契约、demo、smoke 和 pytest 检查，但不会运行 `git diff --check`。
- 期望结果：release gate 应包含 `git diff --check`，让尾随空格、冲突标记等 diff whitespace 问题在发布前一键检查中失败。

## 原因

- 根因：`scripts/release_check.sh` 没有把 Git whitespace 检查纳入固定门禁；只能依赖人工额外运行 `git diff --check`。
- 影响范围：发布前质量门禁、GitHub 提交前检查、当前小阶段提交前验证。

## 修复

- 修改文件：`scripts/release_check.sh`、`tests/test_release_contracts.py`
- 关键行为：在 `scripts/release_check.sh` 前段加入 `git diff --check`，并用 release contract 测试固定该门禁。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_rejects_whitespace_errors -q` 失败，`scripts/release_check.sh` 中缺少 `git diff --check`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_rejects_whitespace_errors tests/test_release_contracts.py::test_release_check_compiles_application_package -q` 通过，`2 passed`；`bash -n scripts/release_check.sh` 通过；`git diff --check` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`934 passed`；`bash scripts/release_check.sh` 通过，包含 `git diff --check` 和 `.venv/bin/python -m pytest -q` 的 `934 passed`。
