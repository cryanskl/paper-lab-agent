# Env validator followed symlinked settings config parent

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_env_example.py`，且仓库内 `app/` 是指向仓库外目录的 symlink。
- 实际结果：validator 跟随 symlink 读取仓库外的 `app/config.py`；如果目标配置合法，校验返回 0。
- 期望结果：validator 应拒绝 symlinked settings config parent，避免 release gate 使用仓库外配置作为 `.env.example` key/default 真相源。

## 原因

- 根因：`scripts/validate_env_example.py` 只拒绝 `app/config.py` 路径自身是 symlink 或非普通文件，没有检查其父目录是否为 symlink。
- 影响范围：release gate 中的 `.env.example` key/default 校验；仓库内 `app/` 被 symlink 替代时，发布检查可能误判通过。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`
- 关键行为：读取 `app/config.py` 前先检查 `first_symlink_parent(SETTINGS_CONFIG_PATH)`，发现 symlinked parent 时输出 `settings config parent is not a regular directory: ...` 并返回非零。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_settings_config_parent -q` 失败，当前 validator 返回 0。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_settings_config_parent -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example_validator"` 通过，`18 passed, 306 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`931 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `931 passed`。
