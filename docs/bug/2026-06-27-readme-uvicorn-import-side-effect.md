# README command validator imported uvicorn target modules

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py <repo>`，且 README 或 release checklist 中记录 `uvicorn demo_app.main:app` 这类本地 ASGI app target。
- 实际结果：validator 为了确认 `app` 属性存在会 import 目标模块，导致目标模块的顶层代码在发布文档校验阶段被执行。
- 期望结果：发布文档校验应验证 repo 内 uvicorn target 是否存在，但不执行被验证模块的顶层代码。

## 原因

- 根因：`uvicorn_target_issue()` 在解析 repo 内 target 时直接调用 `__import__()`，再用 `getattr()` 判断属性是否存在。
- 影响范围：README 命令发布校验、release checklist 命令校验、对临时 release checkout 或指定目录执行 validator 时的副作用边界。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：repo 内 uvicorn target 改为静态解析模块文件，确认模块文件在 repo 内且 top-level `app` 名称存在；不再 import repo 内模块。仓库外 target 继续返回 `uvicorn target outside repository`，缺失 target 继续返回 `uvicorn target missing`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_does_not_import_uvicorn_target_module -q` 失败，validator 返回通过但写出了 `executed.txt`，说明目标模块顶层代码被执行。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_does_not_import_uvicorn_target_module tests/test_release_contracts.py -q -k "readme_commands"` 通过，`23 passed, 264 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`861 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `861 passed`。
