# Vector store accepted empty vector IDs

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 `vector-index.json` 顶层包含空字符串 key，例如 `{"": {...}}`，系统状态会报告 `valid_json=true`；RAG 查询会返回带空 `vector_id` 的结果。
- 期望结果：本地 vector store 的记录 ID 必须是非空字符串；空 ID 不能通过健康检查或查询读取。

## 原因

- 根因：`app/services/rag.py` 读取本地 vector store 时逐条校验记录内容，但没有校验顶层 key 本身。
- 影响范围：RAG 引用溯源、系统健康检查、release readiness。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：读取本地 vector store 时要求每条记录的 `vector_id` 是非空字符串；异常时抛出 `vector store record id must be a non-empty string`，系统状态将 `valid_json` 标为 `false` 并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_empty_vector_id_returns_clear_error tests/test_api.py::test_system_status_reports_empty_vector_id -q` 失败，RAG 返回 `200`，系统状态返回 `valid_json=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_empty_vector_id_returns_clear_error tests/test_api.py::test_system_status_reports_empty_vector_id tests/test_api.py::test_rag_query_unsupported_vector_embedding_model_returns_clear_error tests/test_api.py::test_system_status_reports_unsupported_vector_embedding_model tests/test_api.py::test_rag_query_invalid_vector_embedding_model_returns_clear_error tests/test_api.py::test_system_status_reports_invalid_vector_embedding_model -q` 通过，`6 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`959 passed`；`bash scripts/release_check.sh` 通过。
