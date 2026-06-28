# System status accepted symlinked storage directories

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `pdf_dir`、`tei_dir`、`translation_dir`、`export_dir` 等本地存储目录健康状态，且其中某个目录本身是 symlink。
- 实际结果：系统状态接口会跟随 symlink 检查目标目录权限；如果目标目录可写，则报告 `writable=true`，release readiness 不产生对应 storage error。
- 期望结果：项目配置的本地存储目录本身不能是 symlink；遇到 symlinked storage dir 时应报告不可写，让 release readiness 标红。

## 原因

- 根因：`app/routers/system.py` 的 `storage_path_health()` 只使用 `path.exists()` 与 `os.access(path, os.W_OK)`，这两个判断都会跟随 symlink。
- 影响范围：系统健康检查、release readiness、本地 PDF/TEI/翻译/导出存储配置诊断可信度。

## 修复

- 修改文件：`app/routers/system.py`、`tests/test_api.py`。
- 关键行为：storage path 本身是 symlink 时仍报告 `exists=true`，但 `writable=false`；release readiness 因此返回如 `pdf_dir.writable` 的 storage error。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_symlinked_storage_dir_not_writable -q` 失败，当前实现返回 `pdf_dir.writable=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_symlinked_storage_dir_not_writable tests/test_api.py::test_health_seed_and_search tests/test_api.py::test_system_status_reports_corrupt_vector_store_health tests/test_api.py::test_system_status_reports_symlinked_vector_store_health_error -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `805 passed`。
