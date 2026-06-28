# Health check accepted symlinked env file

## 现象

- 触发命令、接口或页面：运行 `python scripts/health_check.py`，且当前目录的 `.env` 是指向仓库外文件的 symlink。
- 实际结果：health check 会跟随 symlink 读取仓库外 `.env`，并用其中的 `API_BASE_URL`、`FRONTEND_URL` 等值决定 live 探测目标。
- 期望结果：`.env` 作为本地运行入口配置时必须来自普通文件树；遇到 symlinked `.env` 应在网络探测前失败，并且不污染当前进程环境变量。

## 原因

- 根因：`scripts/health_check.py` 的 `load_env_file()` 只判断 `.env` 是否存在，随后直接 `read_text()`，没有检查文件本身是否为 symlink 或非普通文件。
- 影响范围：发布健康检查、演示前 live gate、使用 `.env` 推导 API/Streamlit URL 的排障流程。

## 修复

- 修改文件：`scripts/health_check.py`、`tests/test_api.py`。
- 关键行为：`load_env_file()` 在读取前拒绝 symlinked `.env`、symlinked 父目录和非普通文件；读取失败返回结构化错误字符串。`main()` 在解析参数和访问 API 前输出 `health_check failed: ...` 并返回非零。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_env_loader_rejects_symlinked_env_file -q` 失败，`load_env_file()` 返回 `None` 且会读取 symlink 目标。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_env_loader_rejects_symlinked_env_file tests/test_api.py::test_health_check_uses_api_base_url_from_env_file tests/test_api.py::test_health_check_env_loader_ignores_invalid_key_names -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "health_check_env"` 通过，`3 passed, 435 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`897 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `897 passed`。
