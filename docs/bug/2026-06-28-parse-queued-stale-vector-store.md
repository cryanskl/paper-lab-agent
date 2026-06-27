# Parse queued left stale vector store records

## 现象

- 触发命令、接口或页面：文档已经索引后，调用 `POST /api/v1/documents/{id}/parse` 重新解析文档。
- 实际结果：路由会立即删除数据库中的旧 `sections`、`chunks`、`translations` 和 `reaction_sets`，并把 `index_status` 置为 `not_indexed`，但本地 JSON vector store 中该文档的旧向量记录仍保留到后台解析任务真正执行后才可能清理。
- 期望结果：重新解析一旦进入 queued/parsing 状态，数据库派生产物和本地 vector store 中该文档的旧向量记录应同步失效，避免 queued 窗口里暴露旧 RAG 证据。

## 原因

- 根因：`app/services/documents.py` 的 `mark_parse_queued` 只清理 SQLite 派生表和文档状态，没有调用 `JsonVectorStore.delete_document(document_id)` 清理持久向量文件。
- 影响范围：重新解析文档时，如果后台任务尚未执行或稍后失败，旧向量文件可能继续包含已被数据库删除的旧 chunk 证据，降低 RAG 和发布健康检查的可审计性。

## 修复

- 修改文件：`app/services/documents.py`、`tests/test_api.py`。
- 关键行为：`POST /api/v1/documents/{id}/parse` 在返回 pending/parsing 前会清理该文档的本地 JSON vector store 记录，并继续保留既有数据库派生产物清理行为。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_document_parse_route_clears_stale_vectors_before_background_task_runs -q`，确认 queued/parsing 后旧 vector store 记录仍存在。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_document_parse_route_clears_stale_vectors_before_background_task_runs tests/test_api.py::test_document_async_routes_mark_queued_status_before_background_tasks_run tests/test_api.py::test_document_index_route_clears_stale_chunks_before_background_task_runs tests/test_api.py::test_document_extract_route_clears_stale_reaction_sets_before_background_task_runs -q`，4 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1024 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1024 passed`。
