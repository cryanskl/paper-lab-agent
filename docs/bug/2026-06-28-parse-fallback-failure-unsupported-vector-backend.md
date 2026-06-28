# Parse fallback failure ignored unsupported vector backend

## 现象

- 触发命令、接口或页面：设置 `VECTOR_DB_BACKEND=faiss` 等当前不支持的向量后端后，后台直接执行 `parse_document(document_id)`，且 GROBID 不可用、本地文本 fallback 读取也失败。
- 实际结果：解析会标记为 `failed`，但旧向量 cleanup 直接使用本地 JSON vector store，绕过 backend registry，没有暴露 unsupported backend 配置错误。
- 期望结果：本地文本 fallback 失败分支里的旧向量 cleanup 应与索引路径使用同一 vector store registry；不支持的 backend 应作为 cleanup 失败写入 `parse_error`。

## 原因

- 根因：`app/services/documents.py` 的 local-text fallback failure 分支直接调用 `JsonVectorStore(settings.vector_db_path).delete_document(document_id)`，没有通过 `get_vector_store(settings)` 检查 `VECTOR_DB_BACKEND`。
- 影响范围：后台解析失败路径、本地解析兜底失败后的证据清理审计，以及非默认 vector backend 配置下的失败可观测性。

## 修复

- 修改文件：`app/services/documents.py`、`tests/test_api.py`。
- 关键行为：本地文本 fallback 失败后，旧向量 cleanup 改为通过 `get_vector_store(settings)` 执行；不支持 backend 时会在既有 `parse_error` 后追加 `vector cleanup failed: ...`。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_parse_document_fallback_failure_reports_unsupported_vector_db_backend -q`，确认 `VECTOR_DB_BACKEND=faiss` 时 parse error 没有记录 cleanup backend 失败。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_parse_document_fallback_failure_reports_unsupported_vector_db_backend tests/test_api.py::test_parse_document_fallback_failure_clears_stale_artifacts tests/test_api.py::test_parse_document_finalization_rejects_unsupported_vector_db_backend tests/test_api.py::test_parse_document_source_validation_reports_unsupported_vector_db_backend tests/test_api.py::test_parse_document_records_failed_status_when_artifact_cleanup_fails -q`，5 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1031 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1031 passed`。
