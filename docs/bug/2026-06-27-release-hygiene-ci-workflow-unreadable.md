# Release hygiene crashed on unreadable CI workflow

## 现象

- 触发命令、接口或页面：调用 `missing_required_ci_release_gate(repo)` 或运行 release hygiene 校验，且 `.github/workflows/ci.yml` 不是 UTF-8 文本或读取阶段抛出 `OSError`。
- 实际结果：函数在读取 CI workflow 时抛出底层异常，例如 `UnicodeDecodeError` traceback。
- 期望结果：release hygiene 检查应返回稳定的 `ci_workflow_unreadable` 缺失项，让 release gate 报告可诊断的 CI 配置问题。

## 原因

- 根因：`scripts/validate_release_hygiene.py` 的 `missing_required_ci_release_gate()` 在确认 workflow 路径是普通文件后，直接调用 `workflow_path.read_text(encoding="utf-8")`；读取和解码错误没有转换为结构化缺失项。
- 影响范围：release hygiene 校验、release gate、CI workflow 完整性检查。

## 修复

- 修改文件：`scripts/validate_release_hygiene.py`、`tests/test_release_contracts.py`。
- 关键行为：CI workflow regular-file 检查通过后，读取失败或解码失败时返回 `["ci_workflow_unreadable"]`；正常 workflow 的 trigger、checkout、Python setup、requirements install、release check 和 timeout 校验保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_reports_unreadable_ci_workflow -q` 失败，函数抛出 `UnicodeDecodeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "release_hygiene_validator"` 通过，`20 passed, 280 deselected`；`.venv/bin/python -m py_compile scripts/validate_release_hygiene.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`907 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `907 passed`。
