# Health check CLI failed after shared release readiness import

## 现象

- 触发命令、接口或页面：执行 `python scripts/health_check.py --help`，或运行 `bash scripts/release_check.sh`。
- 实际结果：`scripts/health_check.py` 在导入 `app.release_readiness` 时抛出 `ModuleNotFoundError: No module named 'app'`，release gate 在 health check help 阶段失败。
- 期望结果：脚本从仓库根目录直接执行时应能导入项目内共享模块，`--help` 返回 0，并继续参与 release gate。

## 原因

- 根因：`scripts/health_check.py` 作为脚本路径执行时，Python 将 `scripts/` 放在 `sys.path[0]`，仓库根目录不一定在 import path 内；共享常量迁入 `app.release_readiness` 后暴露了这个路径缺口。
- 影响范围：发布 gate、手动运行 health check CLI、任何依赖 `scripts/health_check.py` 直接执行的运维命令。

## 修复

- 修改文件：`scripts/health_check.py`、`tests/test_api.py`。
- 关键行为：在导入 `app.release_readiness` 前，将仓库根目录加入 `sys.path`，与 `scripts/export_openapi.py` 等脚本保持一致；新增 CLI help 回归测试锁定直接执行路径。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_cli_help_runs_with_app_imports -q` 失败，`ModuleNotFoundError: No module named 'app'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_cli_help_runs_with_app_imports tests/test_api.py::test_release_blocking_config_warning_codes_are_shared tests/test_api.py::test_release_blocking_config_warning_codes_are_not_redeclared tests/test_api.py::test_health_check_summary_surfaces_blocking_config_warnings tests/test_frontend_api.py::test_release_readiness_display_state_surfaces_only_blocking_config_warnings -q` 通过，`5 passed`。
- 完整 gate：`.venv/bin/python -m pytest` 通过，`1041 passed`；`bash scripts/release_check.sh` 通过，包含全量 pytest `1041 passed`。
