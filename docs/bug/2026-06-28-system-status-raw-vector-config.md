# System status reported raw vector config values

## 现象

- 触发命令、接口或页面：设置 `EMBEDDING_MODEL=" LOCAL-HASH "` 或 `VECTOR_DB_BACKEND=" LOCAL-JSON "` 后访问 `GET /api/v1/system/status`。
- 实际结果：配置警告不会报 unsupported，但 `external_capabilities.embedding_model` / `external_capabilities.vector_db_backend` 返回原始带空白和大小写变化的值。
- 期望结果：系统状态应报告实际生效的规范值 `local-hash` / `local-json`，和运行时 adapter / backend 选择保持一致。

## 原因

- 根因：`app/routers/system.py` 的 warning 判断使用了归一化逻辑，但 `external_capabilities` 直接返回 `settings` 原始值。
- 影响范围：系统状态接口、release smoke 诊断、发布交接时的配置可读性。

## 修复

- 修改文件：`app/routers/system.py`、`tests/test_api.py`。
- 关键行为：`/system/status` 输出 effective normalized embedding/vector backend names。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_normalized_effective_vector_config -q`，确认返回原始 `" LOCAL-HASH "` 导致失败。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_normalized_effective_vector_config tests/test_api.py::test_system_status_reports_vector_db_backend tests/test_api.py::test_system_status_accepts_normalizable_vector_embedding_model tests/test_api.py::test_system_status_accepts_normalizable_vector_db_backend_metadata -q`，4 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，973 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过；smoke 输出 `system_embedding_model=local-hash`、`system_vector_db_backend=local-json`。
