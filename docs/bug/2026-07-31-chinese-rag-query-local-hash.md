# 中文问题无法检索英文论文切块

## 现象

- 触发命令、接口或页面：在 AI 问答中选择当前英文论文，提问“这篇论文的核心结论是什么？”。
- 实际结果：旧实现把中文问题分词为 `[]`，`POST /api/v1/rag/query` 返回“证据不足：当前索引中没有检索到足够相关的段落。”。
- 期望结果：中文问题能够跨语言召回英文论文切块，并返回带 `chunk_id` / `vector_id` 的可点击引用。

## 原因

- 根因：`app/services/rag.py` 的 `local-hash` 仅提取 ASCII token；更关键的是查询端固定调用 `local_hash_embedding(question)`，没有使用索引端配置的 embedding adapter。
- 影响范围：中文或其他非 ASCII 问题查询英文索引时无法产生有效查询向量；切换 embedding 配置后还可能误用旧向量空间。

## 修复

- 修改文件：`app/services/rag.py`、`app/rag_registry.py`、`app/routers/system.py`、`requirements.txt`、`.env.example`、`scripts/doctor.py`、`docs/接口设计文档.md` 及相关测试。
- 关键行为：新增 `bge-m3` embedding adapter 和 Chroma 持久化后端；查询与索引使用同一 adapter；查询过滤模型或后端元数据不匹配的向量；保留 `local-hash + local-json` 作为离线确定性测试基线。

## 验证

- RED 证据：修复前中文问题的 tokenizer 输出为空，真实接口返回 0 个来源与“证据不足”；对应英文问题可召回 5 个来源。
- GREEN 证据：真实运行配置 `EMBEDDING_MODEL=bge-m3`、`VECTOR_DB_BACKEND=chroma` 下重建文档 1 的 5 个切块；同一句中文问题通过 HTTP 返回 5 个来源，首条为 `Conclusion`，top 相似度 0.522；浏览器页面显示 5 个引用且控制台无错误或警告。
- 完整 gate：`EMBEDDING_MODEL=local-hash VECTOR_DB_BACKEND=local-json VECTOR_DB_PATH=data/vector-index.json bash scripts/release_check.sh` → `1375 passed in 188.74s`。
