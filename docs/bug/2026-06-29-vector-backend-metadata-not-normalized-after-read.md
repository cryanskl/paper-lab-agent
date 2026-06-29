# Vector backend metadata was not normalized after read

## 现象

- 触发命令、接口或页面：`parse_vector_store_json()` 读取本地 JSON vector store，记录中的 `vector_db_backend` 为可规范化值，例如 ` LOCAL-JSON `。
- 实际结果：记录通过校验并可用于 RAG 查询，但返回的数据仍保留原始大小写和空格。
- 期望结果：合法的 `vector_db_backend` 应写回规范化后的值，例如 `local-json`，和 `embedding_model` 的读取行为保持一致。

## 原因

- 根因：`parse_vector_store_json()` 对 `vector_db_backend` 只调用 `normalize_vector_db_backend()` 做支持性校验，没有把规范化结果写回 record。
- 影响范围：RAG 向量库诊断元数据、后续 adapter 排障、发布验收中对 vector store backend 的一致性判断。

## 修复

- 修改文件：`app/services/rag.py`、`tests/test_api.py`。
- 关键行为：`vector_db_backend` 字段存在且合法时，写回规范化后的 backend；非法、空白或非字符串值仍按原有错误路径失败。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_accepts_normalizable_vector_db_backend_metadata -q` 失败，`vector_db_backend` 仍为 ` LOCAL-JSON `。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_rag_query_accepts_normalizable_vector_db_backend_metadata tests/test_api.py::test_rag_query_invalid_vector_db_backend_returns_clear_error tests/test_api.py::test_rag_query_unsupported_vector_db_backend_returns_clear_error tests/test_api.py::test_rag_query_treats_normalizable_embedding_model_as_local_hash -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1262 passed。
