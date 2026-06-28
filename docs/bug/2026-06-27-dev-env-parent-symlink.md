# Dev env loader accepted symlinked env parent

## 现象

- 触发命令、接口或页面：运行 `source scripts/env.sh; load_env_file_if_unset linked/.env`，其中 `linked` 是指向仓库外目录的 symlink。
- 实际结果：上一阶段只拒绝 `.env` 文件本身是 symlink；当父目录是 symlink 时，`load_env_file_if_unset()` 仍会跟随父目录读取仓库外 `.env` 并返回成功。
- 期望结果：`.env` 的父目录链也必须来自普通目录；遇到 symlinked parent 应返回非零并报告具体父目录，不继续读取目标文件。

## 原因

- 根因：`scripts/env.sh` 只检查 `env_file` 自身是否为 symlink 或非普通文件，没有遍历 `env_file` 的父目录组件。
- 影响范围：Quick Start、`scripts/dev.sh`、CI 中 `DEV_EXIT_AFTER_READY=true bash scripts/dev.sh` 的统一启动配置可信度。

## 修复

- 修改文件：`scripts/env.sh`、`tests/test_api.py`。
- 关键行为：`load_env_file_if_unset()` 在读取前遍历相对或绝对 env 路径的父目录组件，发现任一父目录是 symlink 时输出 `env file parent is not a regular directory: ...` 并返回 `1`；普通 `.env` 和缺失 `.env` 行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_env_loader_rejects_symlinked_env_parent -q` 失败，`load_env_file_if_unset linked/.env` 实际返回 `0`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_env_loader_rejects_symlinked_env_parent tests/test_api.py::test_env_loader_rejects_symlinked_env_file tests/test_api.py::test_env_loader_preserves_existing_environment_values tests/test_api.py::test_dev_api_base_url_tracks_runtime_port_override -q` 通过，`4 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "env_loader or dev_api_base_url"` 通过，`8 passed, 432 deselected`；`bash -n scripts/env.sh scripts/dev.sh` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`899 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `899 passed`。
