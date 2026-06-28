# Env validator crashed on unreadable settings config

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_env_example.py`，且仓库内 `app/config.py` 存在但不可读取或不是 UTF-8 文本。
- 实际结果：validator 在读取 settings 配置时抛出 `UnicodeDecodeError` 或 `OSError`，release gate 输出 traceback。
- 期望结果：配置契约校验应返回稳定错误，指出 settings config 不可读，并以非零状态退出。

## 原因

- 根因：主入口只预检查了 `.env.example` 本身，后续 `missing_required_keys()` 会继续读取 `app/config.py` 提取 `Settings` alias，但该读取没有在 CLI 层转换为可读错误。
- 影响范围：`.env.example` 发布契约校验；坏的配置文件会中断 release gate，而不是给出可修复的文件级错误。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`
- 关键行为：主入口在执行键、默认值和 runtime drift 校验前读取 `app/config.py`；读取或解码失败时输出 `settings config unreadable: ...`，返回 `1`，不再输出 traceback。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_reports_unreadable_settings_config -q` 失败，当前实现输出 `UnicodeDecodeError` traceback。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_reports_unreadable_settings_config -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example_validator or env_example_contains or env_example_defaults or env_example_keeps"` 通过，`13 passed, 294 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`914 passed`；`bash scripts/release_check.sh` 通过。
