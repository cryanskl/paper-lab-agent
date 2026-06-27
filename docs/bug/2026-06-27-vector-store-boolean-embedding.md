# Vector store accepted boolean embeddings

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 vector 记录的 `embedding` 包含 `true` 或 `false` 时，系统状态会报告 `valid_json=true`；RAG 查询把布尔值当作数值向量处理或静默返回无证据结果。
- 期望结果：`embedding` 只能包含真实数值，布尔值不能作为向量维度通过健康检查或查询读取。

## 原因

- 根因：`app/services/rag.py` 用 `isinstance(value, (int, float))` 判断向量数值；Python 中 `bool` 是 `int` 的子类，导致 `true`/`false` 被误接受。
- 影响范围：系统健康检查、release readiness、RAG 查询可信度。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：新增向量数值判断，显式排除 `bool`；遇到布尔 embedding 时抛出 `vector store record embedding must be a numeric array: <vector_id>`，系统状态将 `valid_json` 标为 `false` 并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_boolean_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_boolean_vector_embedding -q` 失败，RAG 返回 `200`，系统状态返回 `valid_json=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_boolean_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_boolean_vector_embedding tests/test_api.py::test_rag_query_malformed_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_malformed_vector_embedding -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`943 passed`；`bash scripts/release_check.sh` 通过。
