# System status marked symlinked storage parents writable

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status`，且 `PAPER_LAB_DATA_DIR` 配置为 symlink 目录，symlink 目标里已经存在 `pdfs`、`tei`、`translations`、`exports` 等子目录。
- 实际结果：`storage_health` 对 `pdf_dir`、`tei_dir`、`translation_dir`、`export_dir` 等子路径只检查路径本身是否 symlink；当子目录存在且可写时会误报 `writable=true`，`release_readiness.storage_errors` 也缺少对应阻断项。
- 期望结果：系统状态诊断应把 symlink parent 下的本地存储路径视为不可写，避免发布健康检查给出过于乐观的 release readiness。

## 原因

- 根因：`app/routers/system.py` 的 `storage_path_health()` 只使用 `path.is_symlink()` 判断路径本身，没有检查父级链是否包含 symlink。
- 影响范围：live runtime 健康检查、`scripts/health_check.py --require-release-ready` 的 API 聚合依据、发布前本地存储诊断。

## 修复

- 修改文件：`app/routers/system.py`、`tests/test_api.py`。
- 关键行为：`storage_path_health()` 复用配置层的 storage path 安全判断；路径本身或父级链包含 symlink 时，`exists` 仍按真实状态报告，但 `writable=false`，并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_symlinked_storage_parent_not_writable -q` 失败，当前实现把 symlinked parent 下的存储子目录误报为 `writable=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_symlinked_storage_parent_not_writable tests/test_api.py::test_system_status_reports_symlinked_storage_dir_not_writable tests/test_api.py::test_system_status_reports_release_readiness -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "system_status_reports_symlinked_storage or system_status_reports_release_readiness or health_check_summary_prefers_api_release_readiness or health_check_summary_only_includes_storage_errors"` 通过，`5 passed, 406 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`842 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `842 passed`。
