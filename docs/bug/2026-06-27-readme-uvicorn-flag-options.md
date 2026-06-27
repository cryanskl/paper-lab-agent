# README command validator skipped uvicorn targets after flag options

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_readme_commands.py <repo>`，且 README 或 release checklist 中记录 `uvicorn --factory app.missing:create_app` 或 `uvicorn --date-header app.missing:app`。
- 实际结果：validator 把 `--factory`、`--date-header` 等布尔 flag 当成带值选项，跳过了紧跟其后的 app target，导致无效 target 不会被报告。
- 期望结果：uvicorn 布尔 flag 不应消耗后续 token；紧跟在 flag 后的 app target 仍应被校验。

## 原因

- 根因：`UVICORN_OPTIONS_WITH_VALUES` 混入了 `--factory`、`--date-header`、`--proxy-headers`、`--server-header`、`--use-colors` 这类布尔 flag。
- 影响范围：README 命令发布校验、release checklist 命令校验、带 uvicorn flag 的启动命令可信度。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：新增 `UVICORN_FLAG_OPTIONS`，布尔 flag 只跳过自身，不消耗下一个 token；真正带值的选项继续按原逻辑跳过其参数。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_reports_uvicorn_target_after_factory_flag -q` 失败，当前实现返回空 issue 列表；`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_reports_uvicorn_target_after_date_header_flag -q` 同样失败。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_reports_uvicorn_target_after_factory_flag tests/test_release_contracts.py::test_readme_commands_validator_reports_uvicorn_target_after_date_header_flag tests/test_release_contracts.py -q -k "readme_commands"` 通过，`27 passed, 264 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`864 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `864 passed`。
