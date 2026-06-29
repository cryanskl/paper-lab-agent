# Env loader ignored file parent paths

## 现象

- 触发命令、接口或页面：`load_env_file_if_unset not-dir/.env` 或 `health_check.load_env_file(Path("not-dir/.env"))`，其中 `not-dir` 已存在且是普通文件。
- 实际结果：shell loader 返回成功，Python health_check loader 返回 `None`，把这个路径当成 `.env` 不存在处理。
- 期望结果：两个 loader 都应返回明确错误：`env file parent is not a regular directory: not-dir`，避免发布前配置路径错误被静默跳过。

## 原因

- 根因：`scripts/env.sh` 的父级遍历只拒绝 symlink，不拒绝已存在的非目录；`scripts/health_check.py` 的 `load_env_file` 同样只检查 env 文件自身和 symlink 父级。
- 影响范围：本地启动脚本、health check 和 release gate 读取 `.env` 时，如果 `.env` 父路径被误建为普通文件，配置加载错误会被误判为没有 `.env`。

## 修复

- 修改文件：`scripts/env.sh`、`scripts/health_check.py`、`tests/test_api.py`
- 关键行为：shell 和 Python env loader 都在加载前拒绝已存在但不是目录的父路径，并保留不存在 `.env` 时不报错的现有语义。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_env_loader_rejects_file_env_parent tests/test_api.py::test_health_check_env_loader_rejects_file_env_parent -q` -> `2 failed`
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_env_loader_rejects_file_env_parent tests/test_api.py::test_env_loader_rejects_symlinked_env_parent tests/test_api.py::test_env_loader_rejects_symlinked_env_file tests/test_api.py::test_health_check_env_loader_rejects_file_env_parent tests/test_api.py::test_health_check_env_loader_rejects_symlinked_env_file tests/test_api.py::test_health_check_uses_api_base_url_from_env_file -q` -> `6 passed`
- 完整 gate：`bash scripts/release_check.sh` -> `1100 passed`
