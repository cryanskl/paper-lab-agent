# RAG vector store followed symlinked parent directories

## 现象

- 触发命令、接口或页面：`index_document()` 写入本地 JSON 向量索引，且 `VECTOR_DB_PATH` 的父目录链包含 symlink。
- 实际结果：`JsonVectorStore` 会跟随 symlink 父目录写入目录外位置，并把文档索引状态标记为 `indexed`。
- 期望结果：本地向量索引路径的父目录链不能包含项目控制外的 symlink；遇到 symlink 父目录时索引失败，不能把 vector store 写到配置目录树之外。

## 原因

- 根因：`app/services/rag.py` 只检查 vector store 文件本身是否是 symlink 或非普通文件，没有检查输出路径父目录链。
- 影响范围：RAG 本地索引、文档索引状态、向量检索数据可信度。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：本地 JSON vector store 读写前扫描路径父目录链；遇到非系统根级 symlink 父目录时索引任务进入 `failed`，`index_error` 记录 `vector store path parent is not a regular directory: ...`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_index_rejects_symlinked_vector_store_parent -q` 失败，当前实现返回 `indexed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_index_rejects_symlinked_vector_store_parent tests/test_api.py::test_rag_index_rejects_symlinked_vector_store tests/test_api.py::test_rag_index_uses_local_vector_store tests/test_api.py::test_index_unparsed_document_records_failed_status -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `803 passed`。
