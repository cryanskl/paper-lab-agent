# export_openapi script could not import app

## 现象

- 触发命令、接口或页面：`.venv/bin/python scripts/export_openapi.py --compact`
- 实际结果：脚本退出并报 `ModuleNotFoundError: No module named 'app'`。
- 期望结果：脚本应可从仓库根目录作为文件直接执行，并输出当前 FastAPI OpenAPI JSON。

## 原因

- 根因：直接执行 `scripts/export_openapi.py` 时，Python 将 `scripts/` 放在 `sys.path[0]`，仓库根目录不在 import path 中，导致 `from app.main import app` 失败。
- 影响范围：README 和 release gate 中记录的 `python scripts/export_openapi.py ...` 命令无法运行，OpenAPI schema 无法在不启动服务的情况下导出。

## 修复

- 修改文件：`scripts/export_openapi.py`、`tests/test_release_contracts.py`
- 关键行为：脚本启动时将仓库根目录加入 `sys.path`；新增 `test_export_openapi_script_runs_as_file` 覆盖直接执行路径。

## 验证

- RED 证据：`test_export_openapi_script_runs_as_file` 失败，stderr 包含 `ModuleNotFoundError: No module named 'app'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_openapi_script_runs_as_file -q` 返回通过；本阶段相关 OpenAPI 导出测试返回 `5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 返回 `634 passed`。
