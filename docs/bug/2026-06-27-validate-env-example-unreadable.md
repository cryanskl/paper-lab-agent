# Env example validator crashed on unreadable file

## 现象

- 触发命令、接口或页面：运行 `python scripts/validate_env_example.py .env.example`，且 `.env.example` 不是 UTF-8 文本或读取阶段抛出 `OSError`。
- 实际结果：脚本在解析 required keys 时抛出底层异常，例如 `UnicodeDecodeError` traceback。
- 期望结果：release gate 应得到稳定的一行错误，指出 `.env.example` 不可读，而不是暴露 Python traceback。

## 原因

- 根因：`scripts/validate_env_example.py` 在确认路径存在且不是 symlink 后，直接通过 `parse_env_values()` 读取文件；读取和解码错误没有在 CLI 层转换为明确失败信息。
- 影响范围：`.env.example` 契约校验、release gate、Quick Start 配置 hygiene 检查。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`。
- 关键行为：regular-file 检查通过后、执行 missing key / secret / default drift 校验前，先用 UTF-8 读取 `.env.example`；读取或解码失败时返回 1，并输出 `env example unreadable: ...`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_reports_unreadable_env_example -q` 失败，stderr 包含 `UnicodeDecodeError` traceback。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example_validator"` 通过，`9 passed, 288 deselected`；`.venv/bin/python -m py_compile scripts/validate_env_example.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`904 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `904 passed`。
