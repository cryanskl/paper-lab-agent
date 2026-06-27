# Parse queue ignored unsupported vector backend

## 现象

- 触发命令、接口或页面：设置 `VECTOR_DB_BACKEND=faiss` 等当前不支持的向量后端后，调用 `POST /api/v1/documents/{id}/parse` 重新解析文档。
- 实际结果：解析排队仍直接使用本地 JSON vector store 清理路径并返回 202，没有暴露 unsupported backend 配置错误，也可能让旧下游产物清理语义与索引路径不一致。
- 期望结果：解析排队应与索引路径使用同一 vector store registry；遇到不支持的后端时返回结构化错误，并把文档解析状态落库为 `failed`。

## 原因

- 根因：`app/services/documents.py` 的 `mark_parse_queued` 直接实例化 `JsonVectorStore(settings.vector_db_path)`，绕过了 `get_vector_store(settings)` 对 `VECTOR_DB_BACKEND` 的规范化和支持性检查。
- 影响范围：非默认 vector backend 配置、未来 Chroma/FAISS 接入前的失败可观测性，以及重新解析时对旧向量证据清理的可信度。

## 修复

- 修改文件：`app/services/documents.py`、`tests/test_api.py`。
- 关键行为：`mark_parse_queued` 改为通过 `get_vector_store(settings)` 获取向量存储；不支持的 backend 会进入已有 queue-failure 分支，清理旧 SQLite 下游产物并返回 `{error:{code:"parse_queue_failed",message}}`。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_document_parse_route_rejects_unsupported_vector_db_backend -q`，确认 `VECTOR_DB_BACKEND=faiss` 时解析排队错误地返回 202。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_document_parse_route_rejects_unsupported_vector_db_backend tests/test_api.py::test_document_parse_route_records_queue_failure_when_vector_store_is_corrupt tests/test_api.py::test_document_parse_route_clears_stale_vectors_before_background_task_runs tests/test_api.py::test_rag_index_rejects_unsupported_vector_db_backend -q`，4 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1028 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1028 passed`。
