# System status marked unsafe vector store as writable

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status`，且 `VECTOR_DB_PATH` 指向 symlink 文件。
- 实际结果：`storage_health.vector_db.valid_json=false`，但同一个 `vector_db` 条目仍报告 `writable=true`。
- 期望结果：symlinked vector store 不符合 RAG 写入规则，系统状态也必须报告 `writable=false`，并在 release readiness 中暴露 `vector_db.writable` 阻断项。

## 原因

- 根因：`vector_store_health()` 只在读取 JSON 前调用 `assert_safe_vector_store_path()`，但 `writable` 字段只由 `os.access(path, os.W_OK)` 决定。
- 影响范围：系统健康检查、发布就绪排障、vector store 本地存储可信度展示。

## 修复

- 修改文件：`app/routers/system.py`、`tests/test_api.py`。
- 关键行为：vector store 路径安全校验结果同时参与 `writable` 与 `valid_json` 判定；路径为 symlink 或父级不安全时，`writable=false`、`valid_json=false`，并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_symlinked_vector_store_health_error -q` 失败，当前实现返回 `writable:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_symlinked_vector_store_health_error tests/test_api.py::test_system_status_reports_corrupt_vector_store_health tests/test_api.py::test_system_status_reports_vector_db_backend -q` 通过，`3 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`848 passed`。
