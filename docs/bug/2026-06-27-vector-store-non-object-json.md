# Vector store accepted non-object JSON

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 `vector-index.json` 内容是 `[]` 这类合法 JSON 但不是对象时，系统状态会报告 `valid_json=true`；RAG 查询运行时再因缺少对象映射接口失败。
- 期望结果：本地 JSON vector store 必须是对象映射；非对象 JSON 应在健康检查和 RAG 查询中都返回明确错误。

## 原因

- 根因：`app/services/rag.py` 只捕获 JSON 解析错误，没有校验解析结果类型；`app/routers/system.py` 也只检查 JSON 语法是否有效。
- 影响范围：系统健康检查、release readiness、RAG 查询错误诊断。

## 修复

- 修改文件：`app/services/rag.py`、`app/routers/system.py`、`tests/test_api.py`。
- 关键行为：新增共享 vector store JSON 解析校验；文件内容不是对象时抛出 `vector store JSON must be an object`，系统状态将 `valid_json` 标为 `false` 并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：当前修复前，`tests/test_api.py::test_system_status_reports_non_object_vector_store_json` 会失败，因为 `valid_json` 被错误标记为 `true`；`tests/test_api.py::test_rag_query_non_object_vector_store_json_returns_clear_error` 会收到低质量内部错误。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_non_object_vector_store_json_returns_clear_error tests/test_api.py::test_system_status_reports_non_object_vector_store_json tests/test_api.py::test_rag_query_backend_failure_returns_json_error tests/test_api.py::test_system_status_reports_corrupt_vector_store_health -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`937 passed`；`bash scripts/release_check.sh` 通过。
