# Vector store rejected normalizable backend metadata on read

## 现象

- 触发命令、接口或页面：已有 `vector-index.json` 中保存 `vector_db_backend: " LOCAL-JSON "` 这类大小写或空白未归一化的旧记录时，访问 `GET /api/v1/system/status` 或 `POST /api/v1/rag/query`。
- 实际结果：系统状态会把 vector store 判为 `valid_json=false`；RAG 查询返回 500。
- 期望结果：读取端应按配置层相同规则归一化 backend 字符串；可归一化为受支持 backend 的旧记录应继续可读。

## 原因

- 根因：`app/services/rag.py` 读取本地 vector store 时直接用原始 `vector_db_backend` 字符串做支持集合判断，没有复用 `normalize_vector_db_backend()`。
- 影响范围：升级后的既有本地索引、系统健康检查、release readiness、RAG 查询。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：读取本地 vector store 时，`vector_db_backend` 仍必须是非空字符串，但支持集合判断前会先归一化；`" LOCAL-JSON "` 可作为 `local-json` 读取，真正不支持的 backend 仍会被拒绝。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_accepts_normalizable_vector_db_backend_metadata tests/test_api.py::test_system_status_accepts_normalizable_vector_db_backend_metadata -q` 失败，RAG 返回 `500`，系统状态返回 `valid_json=false`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_accepts_normalizable_vector_db_backend_metadata tests/test_api.py::test_system_status_accepts_normalizable_vector_db_backend_metadata tests/test_api.py::test_rag_query_invalid_vector_db_backend_returns_clear_error tests/test_api.py::test_system_status_reports_invalid_vector_db_backend tests/test_api.py::test_rag_query_unsupported_vector_db_backend_returns_clear_error tests/test_api.py::test_system_status_reports_unsupported_vector_db_backend -q` 通过，`6 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`970 passed`；`bash scripts/release_check.sh` 通过。
