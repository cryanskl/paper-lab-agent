# Env validator followed symlinked validator script

## 现象

- 触发命令、接口或页面：通过 symlinked `scripts/validate_env_example.py` 运行 `.env.example` 校验，且 symlink 目标位于仓库外。
- 实际结果：validator 跟随 symlink 计算 `REPO_ROOT`，读取仓库外的 `app/config.py` 和 `scripts/dev.sh`；如果目标文件合法，校验返回 0。
- 期望结果：validator 应拒绝 symlinked validator script，避免 release gate 自身的真相源被仓库外脚本路径替代。

## 原因

- 根因：`scripts/validate_env_example.py` 使用 `Path(__file__).resolve()` 推导 `REPO_ROOT`，但没有先检查 `__file__` 路径自身是否为 symlink。
- 影响范围：`.env.example` key/default 校验、runtime 默认值校验，以及 release gate 对仓库内配置和启动脚本的信任边界。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`
- 关键行为：保留真实路径用于 `REPO_ROOT` 推导，但在 `main()` 入口先检查 `SCRIPT_PATH`；发现 symlinked validator script 时输出 `validator script is not a regular file: ...` 并返回非零。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_validator_script -q` 失败，当前 validator 返回 0。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_validator_script -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example_validator"` 通过，`19 passed, 306 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`932 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `932 passed`。
