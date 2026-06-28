# Vector store accepted invalid section IDs

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 vector 记录包含非整数 `section_id`，例如 `[]` 时，系统状态会报告 `valid_json=true`；RAG 查询会继续读取该记录并返回 200。
- 期望结果：`section_id` 如果存在，必须是非布尔正整数；类型错误不能通过健康检查或查询读取。

## 原因

- 根因：`app/services/rag.py` 读取本地 vector store 时没有校验 `section_id` 元数据，导致损坏的来源定位字段被当作健康索引的一部分。
- 影响范围：RAG 来源定位、系统健康检查、release readiness。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：读取本地 vector store 时，如果记录包含 `section_id`，要求它是非布尔正整数；异常时抛出 `vector store record section_id must be a positive integer: <vector_id>`，系统状态将 `valid_json` 标为 `false` 并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_invalid_vector_section_id_returns_clear_error tests/test_api.py::test_system_status_reports_invalid_vector_section_id -q` 失败，RAG 返回 `200`，系统状态返回 `valid_json=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_invalid_vector_section_id_returns_clear_error tests/test_api.py::test_system_status_reports_invalid_vector_section_id tests/test_api.py::test_rag_query_invalid_vector_chunk_id_returns_clear_error tests/test_api.py::test_system_status_reports_invalid_vector_chunk_id tests/test_api.py::test_rag_query_string_vector_document_id_returns_clear_error tests/test_api.py::test_system_status_reports_string_vector_document_id -q` 通过，`6 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`967 passed`；`bash scripts/release_check.sh` 通过。
