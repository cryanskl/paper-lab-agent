# Vector store accepted invalid text

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 vector 记录的 `text` 是数组等非字符串时，系统状态会报告 `valid_json=true`；RAG 查询会暴露内部错误，例如 `'list' object has no attribute 'lower'`。
- 期望结果：每条 vector 记录的 `text` 必须是非空字符串；类型错误不能通过健康检查或查询读取。

## 原因

- 根因：`app/services/rag.py` 读取本地 vector store 时校验了记录对象、`document_id` 和 `embedding`，但没有校验 `text` 类型；local-hash 查询预过滤会对 `text.lower()` 做分词。
- 影响范围：系统健康检查、release readiness、RAG 查询错误诊断和可信度。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：读取本地 vector store 时要求 `text` 是非空字符串；异常时抛出 `vector store record text must be a non-empty string: <vector_id>`，系统状态将 `valid_json` 标为 `false` 并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_non_string_vector_text_returns_clear_error tests/test_api.py::test_system_status_reports_non_string_vector_text -q` 失败，RAG 返回 `'list' object has no attribute 'lower'`，系统状态返回 `valid_json=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_non_string_vector_text_returns_clear_error tests/test_api.py::test_system_status_reports_non_string_vector_text tests/test_api.py::test_rag_query_string_vector_document_id_returns_clear_error tests/test_api.py::test_system_status_reports_string_vector_document_id tests/test_api.py::test_rag_query_empty_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_empty_vector_embedding -q` 通过，`6 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`953 passed`；`bash scripts/release_check.sh` 通过。
