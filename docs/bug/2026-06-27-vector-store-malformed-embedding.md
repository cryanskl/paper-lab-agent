# Vector store accepted malformed embeddings

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 vector 记录是对象、但 `embedding` 是字符串等非数值数组时，系统状态会报告 `valid_json=true`；RAG 查询可能静默返回无证据结果，掩盖本地索引损坏。
- 期望结果：每个 vector 记录的 `embedding` 必须是数值数组；结构错误应在健康检查和 RAG 查询中返回明确错误。

## 原因

- 根因：`app/services/rag.py` 的 vector store JSON 解析只校验顶层对象和记录对象，没有校验 `embedding` 类型。
- 影响范围：系统健康检查、release readiness、RAG 查询可信度。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：解析本地 vector store 时确认每条记录的 `embedding` 是数值数组；遇到异常时抛出 `vector store record embedding must be a numeric array: <vector_id>`，系统状态将 `valid_json` 标为 `false` 并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_malformed_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_malformed_vector_embedding -q` 失败，RAG 返回 `200` 并静默无证据，系统状态返回 `valid_json=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_malformed_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_malformed_vector_embedding tests/test_api.py::test_rag_query_malformed_vector_store_record_returns_clear_error tests/test_api.py::test_system_status_reports_malformed_vector_store_record -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`941 passed`；`bash scripts/release_check.sh` 通过。
