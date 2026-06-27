# Vector store exposed internal error for invalid backend metadata

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 vector 记录包含非字符串 `vector_db_backend`，例如 `[]` 时，系统状态和 RAG 错误消息会暴露 Python 内部错误 `unhashable type: 'list'`。
- 期望结果：`vector_db_backend` 如果存在，必须是非空字符串；类型错误应返回稳定的业务错误，不能泄漏内部异常细节。

## 原因

- 根因：`app/services/rag.py` 对 `vector_db_backend` 直接执行集合 membership 检查，没有先校验字段类型；列表等不可哈希值会触发 Python `TypeError`。
- 影响范围：系统健康检查、release readiness、RAG 查询错误可诊断性。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：读取本地 vector store 时，如果记录包含 `vector_db_backend`，先要求它是非空字符串，再判断是否属于 `SUPPORTED_VECTOR_DB_BACKENDS`；类型异常时抛出 `vector store record vector_db_backend must be a non-empty string: <vector_id>`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_invalid_vector_db_backend_returns_clear_error tests/test_api.py::test_system_status_reports_invalid_vector_db_backend -q` 失败，错误消息为 `unhashable type: 'list'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_invalid_vector_db_backend_returns_clear_error tests/test_api.py::test_system_status_reports_invalid_vector_db_backend tests/test_api.py::test_rag_query_unsupported_vector_db_backend_returns_clear_error tests/test_api.py::test_system_status_reports_unsupported_vector_db_backend -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`963 passed`；`bash scripts/release_check.sh` 通过。
