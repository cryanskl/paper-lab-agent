# Release hygiene crashed on unreadable gitignore

## 现象

- 触发命令、接口或页面：运行 `python scripts/validate_release_hygiene.py .gitignore`，且 `.gitignore` 不是 UTF-8 文本或读取阶段抛出 `OSError`。
- 实际结果：脚本在解析 ignore pattern 时抛出底层异常，例如 `UnicodeDecodeError` traceback。
- 期望结果：release gate 应得到稳定的一行错误，指出 `.gitignore` 不可读，而不是暴露 Python traceback。

## 原因

- 根因：`scripts/validate_release_hygiene.py` 在确认 `.gitignore` 是普通文件后，直接通过 `load_gitignore_patterns()` 读取文件；读取和解码错误没有在 CLI 层转换为明确失败信息。
- 影响范围：release hygiene 校验、release gate、CI 的忽略规则与产物卫生检查。

## 修复

- 修改文件：`scripts/validate_release_hygiene.py`、`tests/test_release_contracts.py`。
- 关键行为：regular-file 检查通过后、执行缺失 pattern / CI release gate / tracked artifacts 校验前，先用 UTF-8 读取 `.gitignore`；读取或解码失败时返回 1，并输出 `gitignore unreadable: ...`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_reports_unreadable_gitignore -q` 失败，stderr 包含 `UnicodeDecodeError` traceback。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "release_hygiene_validator"` 通过，`19 passed, 280 deselected`；`.venv/bin/python -m py_compile scripts/validate_release_hygiene.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`906 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `906 passed`。
