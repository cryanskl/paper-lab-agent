# Env validator followed symlinked dev script

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_env_example.py`，且仓库内 `scripts/dev.sh` 是指向仓库外文件的 symlink。
- 实际结果：validator 跟随 symlink 读取目标脚本；如果目标脚本包含 `DEV_READY_TIMEOUT` 默认值，校验返回 0。
- 期望结果：validator 应拒绝 symlinked dev script，避免 release gate 使用仓库外启动脚本作为 runtime 默认值真相源。

## 原因

- 根因：`scripts/validate_env_example.py` 主入口只在 `DEV_SCRIPT_PATH.exists()` 时读取脚本内容，没有先检查 `DEV_SCRIPT_PATH` 路径自身是否为 symlink 或非普通文件。
- 影响范围：release gate 中的 `.env.example` runtime 默认值校验；仓库内启动脚本被 symlink 替代时，发布检查可能误判通过。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`
- 关键行为：读取 `scripts/dev.sh` 前先拒绝 symlink 或非普通文件，输出 `dev script is not a regular file: ...` 并返回非零。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_dev_script -q` 失败，当前 validator 返回 0。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_dev_script -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example_validator"` 通过，`14 passed, 306 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`927 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `927 passed`。
