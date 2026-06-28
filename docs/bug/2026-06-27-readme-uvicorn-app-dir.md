# README command validator ignored uvicorn app-dir

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py <repo>`，且 README 或 release checklist 中记录 `uvicorn --app-dir src demo_app.main:app` 这类从子目录加载 ASGI app 的命令。
- 实际结果：validator 仍按 repo 根目录解析 `demo_app.main:app`，因此会把 src layout 中真实存在的 target 误报为缺失。
- 期望结果：validator 应尊重 `--app-dir`，按指定目录解析 uvicorn app target，同时仍保证解析出的模块路径不逃出 repo。

## 原因

- 根因：`uvicorn_app_refs()` 只返回 app target 字符串，丢失了同一命令中的 `--app-dir` 配置；`uvicorn_target_issue()` 因此只能使用 repo 根目录作为搜索根。
- 影响范围：README 命令发布校验、release checklist 命令校验、采用 `src/` layout 或其他 app-dir layout 的启动文档可信度。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：`uvicorn_app_refs()` 同时返回 target 与 `--app-dir`；target 校验使用 app-dir 作为模块搜索根，并拒绝逃出 repo 或经过 symlink 的 app-dir。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_resolves_uvicorn_target_from_app_dir -q` 失败，当前实现误报 `demo_app.main:app` 缺失。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_resolves_uvicorn_target_from_app_dir tests/test_release_contracts.py -q -k "readme_commands"` 通过，`27 passed, 264 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`865 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `865 passed`。
