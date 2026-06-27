# Vector store accepted unsupported backend metadata

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 vector 记录包含 `vector_db_backend: "unsupported-backend"` 时，系统状态会报告 `valid_json=true`；RAG 查询会继续读取该记录并返回结果。
- 期望结果：如果 vector 记录声明了 `vector_db_backend`，它必须属于当前服务支持的 vector store backend 集合；不受支持的 backend 不能通过健康检查或查询读取。

## 原因

- 根因：`app/services/rag.py` 写入 vector 记录时包含 `vector_db_backend` 元数据，但读取本地 vector store 时没有校验该字段。
- 影响范围：系统健康检查、release readiness、RAG 索引可信度。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：读取本地 vector store 时，如果记录包含 `vector_db_backend`，要求它属于 `SUPPORTED_VECTOR_DB_BACKENDS`；异常时抛出 `vector store record vector_db_backend is unsupported: <vector_id>`，系统状态将 `valid_json` 标为 `false` 并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_unsupported_vector_db_backend_returns_clear_error tests/test_api.py::test_system_status_reports_unsupported_vector_db_backend -q` 失败，RAG 返回 `200`，系统状态返回 `valid_json=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_unsupported_vector_db_backend_returns_clear_error tests/test_api.py::test_system_status_reports_unsupported_vector_db_backend tests/test_api.py::test_rag_query_unsupported_vector_embedding_model_returns_clear_error tests/test_api.py::test_system_status_reports_unsupported_vector_embedding_model tests/test_api.py::test_rag_query_empty_vector_id_returns_clear_error tests/test_api.py::test_system_status_reports_empty_vector_id -q` 通过，`6 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`961 passed`；`bash scripts/release_check.sh` 通过。
