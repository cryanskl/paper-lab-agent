# README command validator accepted uvicorn targets outside the repository

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py`，且 README 或 release checklist 中记录的 `uvicorn` app target 指向仓库外模块，例如标准库或已安装包。
- 实际结果：validator 只检查 Python 是否能 import 该 target 并找到属性；像 `os:path` 这类仓库外模块 target 会被当作有效本地启动入口。
- 期望结果：发布文档中的 `uvicorn` target 必须来自当前仓库；仓库外模块应被报告为无效，避免交付文档指向非项目 app。

## 原因

- 根因：`uvicorn_target_exists()` 直接 `__import__()` 文档里的模块名并检查属性，没有检查模块 spec 的真实来源路径是否位于 repo 内。
- 影响范围：README 命令发布校验、release checklist 命令校验、统一启动命令文档的本地 app target 可信度。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：解析 `uvicorn` module spec；如果模块不存在或属性缺失，继续报告 `uvicorn target missing`；如果模块来源不在当前 repo 内，报告 `uvicorn target outside repository`；当前仓库内的 `app.main:app` 等目标继续通过。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_uvicorn_target_outside_repo -q` 失败，当前实现返回空 issue 列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_rejects_uvicorn_target_outside_repo -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "readme_commands"` 通过，`17 passed, 264 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`856 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `856 passed`。
