# Env validator crashed on unreadable dev script

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_env_example.py`，且仓库内 `scripts/dev.sh` 存在但不可读取或不是 UTF-8 文本。
- 实际结果：validator 在读取 dev 启动脚本以比对 `DEV_READY_TIMEOUT` 默认值时抛出 `UnicodeDecodeError` 或 `OSError`，release gate 输出 traceback。
- 期望结果：`.env.example` runtime 默认值校验应返回稳定错误，指出 dev script 不可读，并以非零状态退出。

## 原因

- 根因：主入口已经预检查 `.env.example` 和 `app/config.py`，但 `script_runtime_default_mismatches()` 会继续通过 `dev_ready_timeout_default()` 读取 `scripts/dev.sh`，该读取失败未转换为 CLI 层错误。
- 影响范围：`.env.example` 发布契约校验；坏的 dev 脚本会中断 release gate，而不是给出可修复的文件级错误。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`
- 关键行为：主入口在执行键、默认值和 runtime drift 校验前读取 `scripts/dev.sh`；读取或解码失败时输出 `dev script unreadable: ...`，返回 `1`，不再输出 traceback。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_reports_unreadable_dev_script -q` 失败，当前实现输出 `UnicodeDecodeError` traceback。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_reports_unreadable_dev_script -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example_validator or env_example_contains or env_example_defaults or env_example_keeps"` 通过，`14 passed, 294 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`915 passed`；`bash scripts/release_check.sh` 通过。
