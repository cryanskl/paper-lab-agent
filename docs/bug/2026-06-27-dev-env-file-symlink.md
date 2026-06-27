# Dev env loader accepted symlinked env file

## 现象

- 触发命令、接口或页面：运行 `bash scripts/dev.sh` 或直接 `source scripts/env.sh; load_env_file_if_unset .env`，且当前目录的 `.env` 是指向仓库外文件的 symlink。
- 实际结果：`load_env_file_if_unset()` 使用 `[[ -f .env ]]` 判断，bash 会跟随 symlink 并读取仓库外 `.env`，统一启动命令可能使用不可信的 API/Streamlit 端口、URL 或外部服务配置。
- 期望结果：`.env` 作为本地启动配置输入时必须是普通文件；遇到 symlinked `.env` 应返回非零并输出稳定错误，不继续读取目标文件。

## 原因

- 根因：`scripts/env.sh` 只检查 `.env` 是否表现为普通文件，未显式拒绝 symlink；`-f` 对指向普通文件的 symlink 返回 true。
- 影响范围：Quick Start、`scripts/dev.sh`、`DEV_EXIT_AFTER_READY=true bash scripts/dev.sh` 启动验证，以及所有复用 `scripts/env.sh` 的本地运行流程。

## 修复

- 修改文件：`scripts/env.sh`、`tests/test_api.py`。
- 关键行为：`load_env_file_if_unset()` 在读取前拒绝 symlinked `.env` 和已存在的非普通文件，向 stderr 输出 `env file is not a regular file: ...` 并返回 `1`；缺失 `.env` 仍按原行为返回成功。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_env_loader_rejects_symlinked_env_file -q` 失败，`load_env_file_if_unset .env` 实际返回 `0`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_env_loader_rejects_symlinked_env_file tests/test_api.py::test_env_loader_preserves_existing_environment_values tests/test_api.py::test_dev_api_base_url_tracks_runtime_port_override -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "env_loader or dev_api_base_url"` 通过，`7 passed, 432 deselected`；`bash -n scripts/env.sh scripts/dev.sh` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`898 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `898 passed`。
