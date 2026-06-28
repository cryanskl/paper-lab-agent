# Vector store accepted empty embeddings

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 vector 记录的 `embedding` 是空数组时，系统状态会报告 `valid_json=true`；RAG 查询静默返回无证据结果，掩盖本地索引损坏。
- 期望结果：`embedding` 必须是非空数值数组；空 embedding 不能通过健康检查或查询读取。

## 原因

- 根因：`app/services/rag.py` 读取本地 vector store 时校验了 embedding 类型、数值有效性和维度一致性，但没有拒绝空数组。
- 影响范围：系统健康检查、release readiness、RAG 查询可信度。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：读取本地 vector store 时拒绝空 embedding；遇到空数组时抛出 `vector store record embedding must not be empty: <vector_id>`，系统状态将 `valid_json` 标为 `false` 并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_empty_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_empty_vector_embedding -q` 失败，RAG 返回 `200`，系统状态返回 `valid_json=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_empty_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_empty_vector_embedding tests/test_api.py::test_rag_query_vector_dimension_mismatch_returns_clear_error tests/test_api.py::test_system_status_reports_vector_dimension_mismatch tests/test_api.py::test_rag_query_non_finite_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_non_finite_vector_embedding -q` 通过，`6 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`949 passed`；`bash scripts/release_check.sh` 通过。
