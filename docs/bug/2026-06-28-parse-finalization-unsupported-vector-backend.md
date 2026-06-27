# Parse finalization ignored unsupported vector backend

## 现象

- 触发命令、接口或页面：设置 `VECTOR_DB_BACKEND=faiss` 等当前不支持的向量后端后，后台直接执行 `parse_document(document_id)` 并进入最终落库阶段。
- 实际结果：最终清理旧向量时直接使用本地 JSON vector store，绕过 backend registry，文档会被错误标记为 `parsed`。
- 期望结果：后台解析最终落库前应与索引路径使用同一 vector store registry；遇到不支持的后端时解析应失败，并记录清晰 `parse_error`。

## 原因

- 根因：`app/services/documents.py` 的 `parse_document` finalization 分支直接调用 `JsonVectorStore(settings.vector_db_path).delete_document(document_id)`，没有通过 `get_vector_store(settings)` 检查 `VECTOR_DB_BACKEND`。
- 影响范围：脚本、测试或后台任务直接调用 `parse_document` 时，非默认 vector backend 配置可能被忽略，导致解析状态和向量清理能力不一致。

## 修复

- 修改文件：`app/services/documents.py`、`tests/test_api.py`。
- 关键行为：`parse_document` 最终落库前改为通过 `get_vector_store(settings)` 清理旧向量；不支持的 backend 会进入既有 finalization failure 分支，落库 `parse_status='failed'` 和 `parse_error`。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_parse_document_finalization_rejects_unsupported_vector_db_backend -q`，确认 `VECTOR_DB_BACKEND=faiss` 时后台解析错误地返回 `parsed`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_parse_document_finalization_rejects_unsupported_vector_db_backend tests/test_api.py::test_parse_document_records_failed_status_when_artifact_cleanup_fails tests/test_api.py::test_parse_document_fallback_failure_clears_stale_artifacts tests/test_api.py::test_document_parse_route_rejects_unsupported_vector_db_backend -q`，4 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1029 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1029 passed`。
