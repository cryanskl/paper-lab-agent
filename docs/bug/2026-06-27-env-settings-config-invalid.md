# Env validator crashed on invalid settings config

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_env_example.py`，且仓库内 `app/config.py` 是可读文本但 Python 语法无效。
- 实际结果：validator 在解析 `Settings` 配置 alias/default 时抛出 `SyntaxError` traceback。
- 期望结果：`.env.example` 配置契约校验应返回稳定错误，指出 settings config 无效，并以非零状态退出。

## 原因

- 根因：主入口只预检查了 `app/config.py` 是否可读，后续 `settings_env_aliases()` / `settings_env_defaults()` 调用 `ast.parse()` 时没有把 `SyntaxError` 转换为 CLI 层错误。
- 影响范围：`.env.example` 发布契约校验；语法损坏的 settings 配置会中断 release gate，而不是给出可修复的文件级错误。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`
- 关键行为：主入口读取 `app/config.py` 后立即执行 `ast.parse()`；语法错误时输出 `settings config invalid: ...`，返回 `1`，不再输出 traceback。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_reports_invalid_settings_config -q` 失败，当前实现输出 `SyntaxError` traceback。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_reports_invalid_settings_config -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example_validator or env_example_contains or env_example_defaults or env_example_keeps"` 通过，`15 passed, 294 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`916 passed`；`bash scripts/release_check.sh` 通过。
