# Local JSON 向量库并发读改写会丢失记录

## 现象

两个文档索引任务同时使用 `VECTOR_DB_BACKEND=local-json` 写入同一个 `VECTOR_DB_PATH` 时，每个 `JsonVectorStore` 实例都可能先读到相同旧快照，再分别覆盖整个 JSON 文件。最终文件通常只保留最后一个写入者的记录；写入中断还可能留下无法解析的半截 JSON。

## 原因

旧版 `upsert_many()` 和 `delete_document()` 的“读取完整文件 → 修改内存字典 → 覆盖完整文件”没有共享临界区。单次 `Path.write_text()` 完成并不代表整个读改写操作具备原子性，不同实例、线程或进程之间也没有互斥。直接覆盖目标文件还会把进程中断风险暴露给读取者和系统健康检查。

## 修复

- 为每个 local JSON 索引创建同目录 `filelock`，锁覆盖读取最新快照、合并或删除以及最终替换的完整读改写过程。
- 在同目录写入独立临时文件，flush + fsync 后通过 `os.replace()` 原子替换目标索引；失败时清理临时文件。
- 将 `filelock` 声明为项目直接依赖并纳入 requirements validator。
- 读取路径继续校验向量文件与锁文件不能是符号链接，保留既有存储安全边界。

## 验证

- 并发回归让两个独立 `JsonVectorStore` 实例同时写入并延长底层写阶段，确认峰值写入者为 1、两条记录全部保留且无临时文件残留。
- 聚焦回归：`.venv/bin/python -m pytest tests/test_api.py tests/test_embeddings.py -q -k 'rag or vector or embedding' --tb=short` → `120 passed, 547 deselected`。
- 依赖契约：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k 'requirements' --tb=short` → `18 passed, 371 deselected`。
- 完整 gate：`bash scripts/release_check.sh` → preflight、demo、health、package、smoke 全部通过；全量测试 `1421 passed, 5 warnings in 248.06s`。
