# RAG index upsert cleanup failure was hidden

## 现象

- 触发命令、接口或页面：后台直接执行 `index_document(document_id)`，文档分块和 embedding 已生成，但写入 vector store 失败，随后失败清理旧向量也失败。
- 实际结果：`index_status` 会被标记为 `failed`，但 `index_error` 只记录原始写入失败，吞掉了后续 `vector cleanup failed`。
- 期望结果：索引失败后的二次向量 cleanup 如果也失败，应追加到 `index_error`，便于发布排障判断是否存在残留向量证据。

## 原因

- 根因：`app/services/rag.py` 的 `index_document()` 通用异常分支在清理 vector store 时捕获异常后直接 `pass`。
- 影响范围：RAG 索引失败路径、向量写入异常后的残留清理审计，以及 release/smoke 失败时的可观测性。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：索引异常后仍会删除 SQLite chunks；如果 vector store cleanup 失败，会把 `vector cleanup failed: ...` 追加到返回值和 `documents.index_error`。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_rag_index_records_cleanup_failure_after_vector_upsert_fails -q`，确认 vector upsert 失败后 cleanup failure 被吞掉。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_rag_index_records_cleanup_failure_after_vector_upsert_fails tests/test_api.py::test_rag_index_records_failed_status_when_vector_cleanup_fails tests/test_api.py::test_rag_index_records_failed_status_when_vector_store_json_is_corrupt tests/test_api.py::test_rag_index_rejects_unsupported_vector_db_backend tests/test_api.py::test_rag_index_fails_when_sections_have_no_indexable_text -q`，5 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1032 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1032 passed`。
