# Index queue failure hid corrupt vector store details

## 现象

- 触发命令、接口或页面：本地 JSON vector store 已损坏时，调用 `POST /api/v1/documents/{id}/index` 重新索引文档。
- 实际结果：排队前清理 vector store 会抛出未处理异常，API 只暴露泛化 500，文档仍保留旧 `index_status` 和旧 chunks。
- 期望结果：排队失败应返回结构化错误，文档索引状态应落库为 `failed`，并清理旧 chunks，便于前端、health check 和发布排查看到真实失败原因。

## 原因

- 根因：`app/services/rag.py` 的 `mark_index_queued` 在清理 vector store 失败时直接抛出异常，没有先记录 `index_status='failed'` 和 `index_error`。
- 影响范围：vector store JSON 损坏、路径不安全或后端配置错误时，重新索引入口可能留下旧索引状态，降低异步任务状态轮询和发布健康检查的可审计性。

## 修复

- 修改文件：`app/services/rag.py`、`app/routers/documents.py`、`tests/test_api.py`。
- 关键行为：`mark_index_queued` 捕获排队前 vector cleanup 失败，清理该文档旧 chunks 并写入失败状态；路由把该失败转换成 `{error:{code:"index_queue_failed",message}}`。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_document_index_route_records_queue_failure_when_vector_store_is_corrupt -q`，确认损坏 vector store 会抛出未处理异常且不会落库失败状态。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_document_index_route_records_queue_failure_when_vector_store_is_corrupt tests/test_api.py::test_document_index_route_clears_stale_vectors_before_background_task_runs tests/test_api.py::test_document_index_route_clears_stale_chunks_before_background_task_runs tests/test_api.py::test_rag_index_records_failed_status_when_vector_store_json_is_corrupt -q`，4 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1026 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1026 passed`。
