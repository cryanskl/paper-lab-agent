# System status crashed when a storage directory path was a file

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status`，且 `PAPER_LAB_PDF_DIR` 等目录型存储路径实际已经存在为普通文件。
- 实际结果：配置层执行 `ensure_dirs()` 时对普通文件调用 `mkdir(..., exist_ok=True)`，接口在生成状态响应前抛出 `FileExistsError`。
- 期望结果：系统状态接口应稳定返回 200，把该路径报告为 `exists=true`、`writable=false`，并在 `release_readiness.storage_errors` 中暴露对应阻断项。

## 原因

- 根因：`Settings.ensure_dirs()` 只跳过 symlink 风险路径，没有跳过“目标已存在但不是目录”的路径；`storage_path_health()` 也只检查存在性、安全性和权限，没有要求目录型路径必须是目录。
- 影响范围：发布前健康检查、`scripts/health_check.py --require-release-ready` 依赖的 API 状态、错误配置下的本地排障。

## 修复

- 修改文件：`app/config.py`、`app/routers/system.py`、`tests/test_api.py`。
- 关键行为：自动创建目录时跳过已存在的非目录路径；系统状态对目录型存储要求 `path.is_dir()`，对数据库路径按文件检查，避免把正常数据库文件误判为不可写目录。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_storage_dir_file_not_writable -q` 失败，`GET /api/v1/system/status` 触发 `FileExistsError: [Errno 17] File exists`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_storage_dir_file_not_writable tests/test_api.py::test_system_status_reports_symlinked_storage_dir_not_writable tests/test_api.py::test_system_status_reports_symlinked_storage_parent_not_writable tests/test_api.py::test_system_status_reports_release_readiness tests/test_config.py -q` 通过，`8 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`850 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `850 passed`。
