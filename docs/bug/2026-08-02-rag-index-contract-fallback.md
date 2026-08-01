# RAG 索引契约错配被词法回退掩盖

## 现象

向量记录由 `bge-m3` 建立、当前配置却切换为 `local-hash`（或向量后端不同）时，`POST /api/v1/rag/query` 会过滤掉不匹配的向量命中，然后直接从 SQLite `chunks` 做词法打分并返回 HTTP 200。响应仍携带旧 `vector_id`，看起来像正常 RAG 命中，用户无法知道索引必须重建。

## 原因

旧查询流程只在向量搜索结果上过滤 `embedding_model` 和 `vector_db_backend`，过滤后为空与“确实没有语义证据”共用同一条词法 fallback。模型切换造成维度不同时，向量搜索甚至会先返回零相似度，同样绕过契约判断。因而配置/索引冲突被错误建模成普通无命中。

## 修复

- 在向量搜索前检查查询范围内所有向量记录的 `embedding_model + vector_db_backend` 契约。
- 任一记录与当前配置不一致时抛出专用 `VectorIndexContractError`；API 返回 `409 rag_index_contract_mismatch`，错误信息列出当前配置、发现的旧契约并提示重建索引。
- 只有索引契约一致、但确实没有足够向量证据时，才允许进入既有的词法不足判断。
- 单篇查询只检查指定文档；全库查询检查整个索引，保持“切换模型或后端必须重建”的项目约束。

## 验证

- RED：构造 `embedding_model=bge-m3`、当前配置为 `local-hash/local-json` 的记录，旧接口返回 200，并从 SQLite chunk 返回词法来源。
- GREEN：同一用例返回 `409 rag_index_contract_mismatch`，消息同时包含配置契约、旧契约和 `Rebuild the index` 操作提示。
- 聚焦回归：`.venv/bin/python -m pytest tests/test_api.py tests/test_embeddings.py -q -k 'rag or vector or embedding' --tb=short` → `120 passed, 547 deselected`。
- 完整 gate：`bash scripts/release_check.sh` → preflight、demo、health、package、smoke 全部通过；全量测试 `1421 passed, 5 warnings in 248.06s`。
