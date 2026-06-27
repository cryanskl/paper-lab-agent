# Env validator reported missing dev script as runtime drift

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_env_example.py`，且仓库内不存在 `scripts/dev.sh`。
- 实际结果：validator 在 runtime 默认值比较阶段输出 `DEV_READY_TIMEOUT default missing from ...`，错误被归类为 `.env.example` runtime drift。
- 期望结果：validator 应在预检阶段直接报告 `dev script not found`，明确指出发布检查缺少启动脚本这个真相源。

## 原因

- 根因：`scripts/validate_env_example.py` 主入口只在 `DEV_SCRIPT_PATH.exists()` 时检查和读取启动脚本；缺失文件会进入后续 `script_runtime_default_mismatches()`，被当作默认值缺失而不是文件缺失。
- 影响范围：release gate 中的 `.env.example` 校验；缺少启动脚本时，错误信息会误导为 env/runtime drift，而不是 checkout 缺少必需文件。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`
- 关键行为：读取和比较 runtime 默认值前，若 `scripts/dev.sh` 不存在则输出 `dev script not found: ...` 并返回非零；symlink、父级 symlink、不可读文件的既有诊断保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_reports_missing_dev_script -q` 失败，当前 validator 输出 runtime defaults drift。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_reports_missing_dev_script -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example_validator"` 通过，`16 passed, 306 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`929 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `929 passed`。
