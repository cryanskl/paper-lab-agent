# 化学库抽取与 RAG 索引并发时数据库锁定

## 现象

文献正在执行 RAG 切分入库时点击“抽取化学库”，`POST /api/v1/documents/{id}/extract-chemistry` 返回 500。后台日志显示 `sqlite3.OperationalError: database is locked`，抽取任务没有进入后台，文档的 `chemistry_status` 仍为 `not_extracted`，页面也没有可供用户判断或重试的明确原因。

## 原因

旧版 `index_document` 在同一个 SQLite 写事务中逐段切分并调用嵌入模型。模型计算 89 个分块期间写锁一直未释放，化学抽取路由无法执行清理旧反应集和写入 `extracting` 状态。默认连接没有显式 WAL 和统一 busy timeout，路由也把锁冲突作为通用 500 返回。化学抽取本身同样把全文扫描与数据库写入放在同一个事务中，会放大其他并发任务的等待时间。

## 修复

1. RAG 索引和化学抽取都改为“短事务读取 → 事务外计算 → 短事务落库”，不在模型嵌入或全文扫描期间持有 SQLite 写锁。
2. 数据库初始化启用 WAL，每个连接设置 10 秒 busy timeout，用于吸收短暂的写入竞争。
3. 抽取排队仍遇到锁时返回 `409 document_busy`，前端显示可重试提示；文献处于解析、翻译、索引或抽取中时，其他处理按钮暂时禁用。
4. 文献卡片展示 `chemistry_error`，无反应或抽取失败不再静默。

## 验证

- 并发回归测试暂停 RAG 嵌入线程后触发化学抽取，确认抽取仍立即进入 `extracting`，随后索引正常完成。
- 锁错误映射、WAL/busy timeout、RAG 失败清理、重复抽取和前端提示定向回归通过。
- 完整 gate：`EMBEDDING_MODEL=local-hash VECTOR_DB_BACKEND=local-json VECTOR_DB_PATH=./data/vector-index.json bash scripts/release_check.sh` → `1380 passed in 225.13s`。
