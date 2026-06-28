# README command validator accepted nested uvicorn attributes

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py <repo>`，且 README 或 release checklist 中记录 `uvicorn demo_app.main:container.missing` 这类嵌套 ASGI app target。
- 实际结果：validator 的静态解析只检查 `container` 这个 top-level 名称是否存在，忽略 `.missing`，因此会把实际不可导入的 nested target 判定为通过。
- 期望结果：无法静态证明完整属性链存在时，repo 内 uvicorn target 应报告 `uvicorn target missing`，不能误放行发布文档。

## 原因

- 根因：`local_uvicorn_target_issue()` 使用 `attribute_path.split(".", 1)[0]` 只验证首段属性；上一阶段为避免 import 副作用而改用静态解析后，没有继续验证嵌套属性链。
- 影响范围：README 命令发布校验、release checklist 命令校验、发布文档里记录的 uvicorn nested target 可信度。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：repo 内静态 uvicorn target 只接受可直接证明的单段 top-level 属性；遇到嵌套属性路径时报告 `uvicorn target missing`，避免误放行。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_reports_missing_nested_uvicorn_attribute -q` 失败，当前实现返回空 issue 列表。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_reports_missing_nested_uvicorn_attribute tests/test_release_contracts.py -q -k "readme_commands"` 通过，`24 passed, 264 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`862 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `862 passed`。
