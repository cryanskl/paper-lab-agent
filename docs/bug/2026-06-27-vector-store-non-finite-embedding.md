# Vector store accepted non-finite embeddings

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查 `VECTOR_DB_PATH`，或 `POST /api/v1/rag/query` 读取本地 JSON vector store。
- 实际结果：当 vector 记录的 `embedding` 包含 `NaN`、`Infinity` 或 `-Infinity` 时，系统状态会报告 `valid_json=true`；RAG 查询把非有限值当作向量维度处理或静默返回无证据结果。
- 期望结果：`embedding` 只能包含有限数值；非有限值不能通过健康检查或查询读取。

## 原因

- 根因：Python 的 `json.loads()` 默认接受 `NaN` / `Infinity`，且 `app/services/rag.py` 只校验 embedding 元素是数值类型，没有校验 `math.isfinite()`。
- 影响范围：系统健康检查、release readiness、RAG 查询可信度。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：向量数值判断改为只接受有限的 int/float，并继续排除 bool；遇到非有限 embedding 时抛出 `vector store record embedding must be a finite numeric array: <vector_id>`，系统状态将 `valid_json` 标为 `false` 并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_non_finite_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_non_finite_vector_embedding -q` 失败，RAG 返回 `200`，系统状态返回 `valid_json=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_non_finite_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_non_finite_vector_embedding tests/test_api.py::test_rag_query_boolean_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_boolean_vector_embedding tests/test_api.py::test_rag_query_malformed_vector_embedding_returns_clear_error tests/test_api.py::test_system_status_reports_malformed_vector_embedding -q` 通过，`6 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`945 passed`；`bash scripts/release_check.sh` 通过。
