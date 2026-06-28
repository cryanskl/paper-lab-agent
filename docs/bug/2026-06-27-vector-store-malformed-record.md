# Vector store accepted malformed records

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 `vector-index.json` 顶层是对象、但某个 vector 记录是 `[]` 这类非对象值时，系统状态会报告 `valid_json=true`；RAG 查询运行时返回 Python 内部错误 `'list' object has no attribute 'get'`。
- 期望结果：本地 JSON vector store 的每个 vector 记录都必须是对象；结构错误应在健康检查和 RAG 查询中返回明确错误。

## 原因

- 根因：`app/services/rag.py` 的 vector store JSON 解析只校验顶层对象，没有校验每个 vector 记录的类型；`app/routers/system.py` 复用该解析入口后也缺少记录级校验。
- 影响范围：系统健康检查、release readiness、RAG 查询错误诊断。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：解析本地 vector store 时逐条确认记录是对象；遇到非对象记录时抛出 `vector store record must be an object: <vector_id>`，系统状态将 `valid_json` 标为 `false` 并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_malformed_vector_store_record_returns_clear_error tests/test_api.py::test_system_status_reports_malformed_vector_store_record -q` 失败，RAG 返回 `'list' object has no attribute 'get'`，系统状态返回 `valid_json=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_malformed_vector_store_record_returns_clear_error tests/test_api.py::test_system_status_reports_malformed_vector_store_record tests/test_api.py::test_rag_query_non_object_vector_store_json_returns_clear_error tests/test_api.py::test_system_status_reports_non_object_vector_store_json -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`939 passed`；`bash scripts/release_check.sh` 通过。
