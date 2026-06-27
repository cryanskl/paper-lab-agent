# README command validator ignored repo argument for uvicorn targets

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py <repo>`，且目标 repo 的 README 或 release checklist 中记录 `uvicorn demo_app.main:app` 这类本地 ASGI app target。
- 实际结果：validator 没有按传入 repo 解析 Python import path；临时或外部 checkout 中真实存在的 uvicorn target 会被报为缺失，或受同进程 `sys.modules` 缓存影响被误判为仓库外模块。
- 期望结果：uvicorn target 应按传入的 repo 路径解析；repo 内模块通过，repo 外模块继续被拒绝。

## 原因

- 根因：`uvicorn_target_issue()` 直接调用 `importlib.util.find_spec()` 和 `__import__()`，没有临时把被验证 repo 放入 `sys.path`，也没有隔离同名模块的 `sys.modules` 缓存。
- 影响范围：README 命令发布校验、release checklist 命令校验、对临时 release checkout 或指定目录执行 validator 的可信度。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：解析 uvicorn target 时临时把传入 repo 加入 `sys.path`，并隔离目标模块及父包的缓存；结束后恢复原缓存状态。缺失模块继续返回结构化 `uvicorn target missing`，仓库外模块继续返回 `uvicorn target outside repository`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_resolves_uvicorn_target_from_repo_argument -q` 失败，当前实现对临时 repo 内存在的 `demo_app.main:app` 抛出 `ModuleNotFoundError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_resolves_uvicorn_target_from_repo_argument tests/test_release_contracts.py -q -k "readme_commands"` 通过，`22 passed, 264 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`860 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `860 passed`。
