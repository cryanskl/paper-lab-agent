# Vector index wrote unnormalized backend metadata

## 现象

- 触发命令、接口或页面：设置 `VECTOR_DB_BACKEND=" LOCAL-JSON "` 后触发文档索引，再访问 `GET /api/v1/system/status` 或 `POST /api/v1/rag/query`。
- 实际结果：索引流程可以启动，因为运行时会归一化 backend 配置；但写入 `vector-index.json` 的 `vector_db_backend` 仍是原始值 `" LOCAL-JSON "`，随后 vector store 健康检查会把刚写出的记录判为不支持。
- 期望结果：配置层接受的大小写/空白变体应在写入 vector metadata 前归一化，避免系统生成自身无法读取的索引。

## 原因

- 根因：`app/services/rag.py` 的 `get_vector_store()` 使用 `normalize_vector_db_backend()` 选择本地 backend，但 `index_document()` 写入记录时直接保存 `settings.vector_db_backend` 原始值。
- 影响范围：文档索引、系统健康检查、release readiness、RAG 查询。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：`index_document()` 写入 vector metadata 时保存归一化后的 backend 名称，例如 `local-json`，与读取端支持集合保持一致。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_index_normalizes_vector_db_backend_metadata -q` 失败，记录里的 `vector_db_backend` 实际为 `" LOCAL-JSON "`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_index_normalizes_vector_db_backend_metadata tests/test_api.py::test_rag_index_uses_local_vector_store -q` 通过，`2 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`968 passed`；`bash scripts/release_check.sh` 通过。
