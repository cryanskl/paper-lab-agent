# Parse queue failure hid corrupt vector store details

## 现象

- 触发命令、接口或页面：本地 JSON vector store 已损坏时，调用 `POST /api/v1/documents/{id}/parse` 重新解析文档。
- 实际结果：排队前清理 vector store 会抛出未处理异常，API 只暴露泛化 500，文档仍可能保留旧解析章节、旧 chunks、旧翻译和旧化学抽取结果。
- 期望结果：解析排队失败应返回结构化错误，文档解析状态应落库为 `failed`，并同步清理该文档旧下游产物，便于前端轮询和发布排查看到真实失败原因。

## 原因

- 根因：`app/services/documents.py` 的 `mark_parse_queued` 在清理 vector store 失败时直接抛出异常，没有先清理 SQLite 下游产物，也没有记录 `parse_status='failed'` 和 `parse_error`。
- 影响范围：vector store JSON 损坏、路径不安全或读取失败时，重新解析入口可能留下旧解析/索引/翻译/化学库证据，降低异步任务状态和发布健康检查的可审计性。

## 修复

- 修改文件：`app/services/documents.py`、`app/routers/documents.py`、`tests/test_api.py`。
- 关键行为：`mark_parse_queued` 捕获排队前 vector cleanup 失败，清理该文档旧 sections/chunks/translations/reaction_sets 并写入失败状态；路由把该失败转换成 `{error:{code:"parse_queue_failed",message}}`。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_document_parse_route_records_queue_failure_when_vector_store_is_corrupt -q`，确认损坏 vector store 会抛出未处理异常且不会清理旧下游产物。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_document_parse_route_records_queue_failure_when_vector_store_is_corrupt tests/test_api.py::test_document_parse_route_clears_stale_vectors_before_background_task_runs tests/test_api.py::test_document_async_routes_mark_queued_status_before_background_tasks_run tests/test_api.py::test_parse_document_fallback_failure_clears_stale_artifacts -q`，4 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1027 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1027 passed`。
