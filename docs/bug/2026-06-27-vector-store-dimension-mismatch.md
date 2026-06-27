# Vector store accepted dimension mismatches

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 vector 记录的 `dimensions` 与 `embedding` 实际长度不一致时，系统状态会报告 `valid_json=true`；RAG 查询可能静默返回无证据结果，掩盖本地索引损坏。
- 期望结果：如果 vector 记录带有 `dimensions`，它必须与 `embedding` 长度一致；不一致时健康检查和 RAG 查询都应返回明确错误。

## 原因

- 根因：`app/services/rag.py` 读取本地 vector store 时校验了 embedding 类型和数值有效性，但没有校验记录里的 `dimensions` 元数据。
- 影响范围：系统健康检查、release readiness、RAG 查询可信度。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：读取本地 vector store 时，如果记录包含 `dimensions`，要求它是非布尔整数且等于 `len(embedding)`；不一致时抛出 `vector store record dimensions must match embedding length: <vector_id>`，系统状态将 `valid_json` 标为 `false` 并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_vector_dimension_mismatch_returns_clear_error tests/test_api.py::test_system_status_reports_vector_dimension_mismatch -q` 失败，RAG 返回 `200`，系统状态返回 `valid_json=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_vector_dimension_mismatch_returns_clear_error tests/test_api.py::test_system_status_reports_vector_dimension_mismatch tests/test_api.py::test_rag_query_non_finite_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_non_finite_vector_embedding tests/test_api.py::test_rag_query_boolean_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_boolean_vector_embedding -q` 通过，`6 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`947 passed`；`bash scripts/release_check.sh` 通过。
