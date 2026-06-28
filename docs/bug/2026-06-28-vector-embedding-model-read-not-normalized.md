# Vector store rejected normalizable embedding model metadata on read

## 现象

- 触发命令、接口或页面：已有 `vector-index.json` 中保存 `embedding_model: " LOCAL-HASH "` 这类大小写或空白未归一化的旧记录时，访问 `GET /api/v1/system/status` 或 `POST /api/v1/rag/query`。
- 实际结果：系统状态会把 vector store 判为 `valid_json=false`；RAG 查询返回 500。
- 期望结果：读取端应按配置层相同规则归一化 embedding model 字符串；可归一化为 `local-hash` 的旧记录应继续可读，并继续使用 local-hash 的文本证据过滤。

## 原因

- 根因：`app/services/rag.py` 读取本地 vector store 时直接用原始 `embedding_model` 字符串做支持集合判断，且后续 RAG 逻辑依赖规范值 `local-hash` 判断是否启用碰撞防护。
- 影响范围：升级后的既有本地索引、系统健康检查、release readiness、RAG 查询证据可信度。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：读取本地 vector store 时，`embedding_model` 仍必须是非空字符串，但支持集合判断前会先归一化；归一化后的模型名写回记录，保证 RAG 后续仍按 `local-hash` 执行文本证据过滤。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_treats_normalizable_embedding_model_as_local_hash tests/test_api.py::test_system_status_accepts_normalizable_vector_embedding_model -q` 失败，RAG 返回 `500`，系统状态返回 `valid_json=false`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_treats_normalizable_embedding_model_as_local_hash tests/test_api.py::test_system_status_accepts_normalizable_vector_embedding_model tests/test_api.py::test_rag_query_invalid_vector_embedding_model_returns_clear_error tests/test_api.py::test_system_status_reports_invalid_vector_embedding_model tests/test_api.py::test_rag_query_unsupported_vector_embedding_model_returns_clear_error tests/test_api.py::test_system_status_reports_unsupported_vector_embedding_model -q` 通过，`6 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`972 passed`；`bash scripts/release_check.sh` 通过。
