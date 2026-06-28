# RAG vector store followed symlinked index path

## 现象

- 触发命令、接口或页面：`index_document()` 写入本地 JSON 向量索引。
- 实际结果：如果 `VECTOR_DB_PATH` 指向的本地索引文件已被替换为 symlink，`JsonVectorStore` 会跟随 symlink 读写目录外文件，并可能把索引状态标记为 `indexed`。
- 期望结果：本地向量索引路径必须是普通文件或不存在；遇到 symlink 或非普通文件时索引失败并记录明确错误，不能覆盖配置路径外的文件。

## 原因

- 根因：`app/services/rag.py` 的 `JsonVectorStore.load()`、`upsert_many()` 和 `delete_document()` 没有拒绝 symlink 或非普通文件路径。
- 影响范围：RAG 本地索引、文档索引状态、向量检索数据可信度。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：本地 JSON vector store 读写前校验目标路径；如果是 symlink 或非普通文件，索引任务进入 `failed`，`index_error` 记录 `vector store path is not a regular file: ...`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_index_rejects_symlinked_vector_store -q` 失败，当前实现返回 `indexed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_index_rejects_symlinked_vector_store tests/test_api.py::test_rag_index_uses_local_vector_store tests/test_api.py::test_index_unparsed_document_records_failed_status -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `799 passed`。
