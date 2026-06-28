# Vector store accepted invalid chunk IDs

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 vector 记录包含非整数 `chunk_id`，例如 `[]` 时，系统状态会报告 `valid_json=true`；RAG 查询会暴露 Python 内部错误 `unhashable type: 'list'`。
- 期望结果：`chunk_id` 如果存在，必须是非布尔正整数；类型错误应返回稳定的业务错误，不能通过健康检查或泄漏内部异常。

## 原因

- 根因：`app/services/rag.py` 读取本地 vector store 时没有校验 `chunk_id` 元数据，后续 RAG 查询把损坏值放进 SQLite 查询参数，触发底层异常。
- 影响范围：RAG 引用溯源、系统健康检查、release readiness。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：读取本地 vector store 时，如果记录包含 `chunk_id`，要求它是非布尔正整数；异常时抛出 `vector store record chunk_id must be a positive integer: <vector_id>`，系统状态将 `valid_json` 标为 `false` 并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_invalid_vector_chunk_id_returns_clear_error tests/test_api.py::test_system_status_reports_invalid_vector_chunk_id -q` 失败，RAG 错误消息为 `unhashable type: 'list'`，系统状态返回 `valid_json=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_invalid_vector_chunk_id_returns_clear_error tests/test_api.py::test_system_status_reports_invalid_vector_chunk_id tests/test_api.py::test_rag_query_string_vector_document_id_returns_clear_error tests/test_api.py::test_system_status_reports_string_vector_document_id tests/test_api.py::test_rag_query_invalid_vector_db_backend_returns_clear_error tests/test_api.py::test_system_status_reports_invalid_vector_db_backend -q` 通过，`6 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`965 passed`；`bash scripts/release_check.sh` 通过。
