# Crawl 自动分类在 SQLite 写事务内阻塞并发写入

## 现象

抓取任务在论文入库后执行自动分类时，会长时间占用 SQLite 写事务。分类器调用外部 LLM 较慢时，文档处理、搜索保存或其它期刊抓取的写操作可能等待 busy timeout，最终出现 `sqlite3.OperationalError: database is locked`；同步分类调用还会阻塞多期刊抓取共用的 asyncio 事件循环。

## 原因

`finalize_crawl_batch()` 原本在同一个 `get_conn()` 写事务中完成论文 upsert、search result 写入、同步分类器调用、自动分类写回和 crawl job 统计更新。论文 upsert 已取得写锁后，`classify_paper()` 才请求分类模型，因此整个外部调用期间写锁都不会释放。此前只把 OpenAlex、Crossref 和 Unpaywall 的网络等待移到了事务外，遗漏了同步 LLM 分类这条外部链路。

## 修复

- 将 crawl finalize 拆成短事务论文落库、事务外分类、短事务自动分类写回和短事务 job 状态更新。
- 通过 `asyncio.to_thread()` 执行同步分类器，避免阻塞并行期刊任务的事件循环。
- 对同一批中去重到相同论文的 `paper_id` 只分类一次，减少重复模型调用。
- 保留原有错误语义：分类失败不会回滚已经完成的抓取，crawl job 仍为 `success`，错误摘要继续写入 `error`；人工分类不会被自动分类覆盖。

## 验证

- RED：分类器内部用第二个 SQLite 连接执行写探针，旧实现得到 `classification failed ... database is locked`，且没有写入自动分类。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_classifier_runs_without_held_sqlite_write_transaction tests/test_api.py::test_crawl_job_auto_classifies_accepted_papers -q --tb=short` → `2 passed`。
- Crawl/多期刊回归：`.venv/bin/python -m pytest tests/test_api.py tests/test_multi_journal_search.py -q -k 'crawl or multi_journal or balanced' --tb=short` → `56 passed, 608 deselected`。
- 完整 gate：`bash scripts/release_check.sh` → preflight、demo、health、package、smoke 全部通过；全量测试 `1419 passed, 5 warnings in 255.08s`。
