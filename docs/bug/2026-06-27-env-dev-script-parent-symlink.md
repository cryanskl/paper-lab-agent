# Env validator followed symlinked dev script parent

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_env_example.py`，且仓库内 `scripts/` 是指向仓库外目录的 symlink。
- 实际结果：validator 跟随 symlinked parent 读取仓库外 `scripts/dev.sh`；如果目标脚本包含 `DEV_READY_TIMEOUT` 默认值，校验返回 0。
- 期望结果：validator 应拒绝 symlinked dev script parent，避免 release gate 使用仓库外启动脚本作为 runtime 默认值真相源。

## 原因

- 根因：`scripts/validate_env_example.py` 主入口只拒绝 `DEV_SCRIPT_PATH` 本身是 symlink 或非普通文件，没有在读取前检查父级目录链。
- 影响范围：release gate 中的 `.env.example` runtime 默认值校验；仓库内 `scripts/` 被 symlink 替代时，发布检查可能误判通过。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`
- 关键行为：读取 `scripts/dev.sh` 前复用 `first_symlink_parent()` 检查父级目录链，命中时输出 `dev script parent is not a regular directory: ...` 并返回非零。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_dev_script_parent -q` 失败，当前 validator 返回 0。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_dev_script_parent -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example_validator"` 通过，`15 passed, 306 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`928 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `928 passed`。
