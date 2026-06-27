# Env validator followed symlinked validator script parent

## 现象

- 触发命令、接口或页面：通过 symlinked `scripts/` 目录下的 `scripts/validate_env_example.py` 运行 `.env.example` 校验，且 `scripts/` 指向仓库外目录。
- 实际结果：validator 跟随 symlinked parent 计算 `REPO_ROOT`，读取仓库外的 `app/config.py` 和 `scripts/dev.sh`；如果目标文件合法，校验返回 0。
- 期望结果：validator 应拒绝 symlinked validator script parent，避免 release gate 自身的真相源被仓库外目录替代。

## 原因

- 根因：`scripts/validate_env_example.py` 只检查脚本路径自身是否为 symlink，没有检查 `__file__` 路径父级链是否包含 symlink。
- 影响范围：`.env.example` key/default 校验、runtime 默认值校验，以及 release gate 对仓库内配置和启动脚本的信任边界。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`
- 关键行为：`main()` 入口检查 `first_symlink_parent(SCRIPT_PATH)`；发现 symlinked validator script parent 时输出 `validator script parent is not a regular directory: ...` 并返回非零。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_validator_script_parent -q` 失败，当前 validator 返回 0。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_validator_script_parent tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_validator_script -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example_validator"` 通过，`20 passed, 306 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`933 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `933 passed`。
