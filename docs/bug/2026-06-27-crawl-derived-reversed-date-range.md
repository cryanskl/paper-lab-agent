# Crawl run accepted derived reversed date ranges

## 现象

- 触发命令、接口或页面：`POST /api/v1/crawl/run` 只传 `date_to`，且同一期刊最近一次成功 `crawl_jobs.date_to` 晚于本次 `date_to`。
- 实际结果：服务会用最近成功 `date_to` 推导 `date_from`，即使推导后 `date_from > date_to`，仍创建 `pending` crawl job 并返回 `202`。
- 期望结果：最终用于抓取的日期范围也必须满足 `date_from <= date_to`；不满足时返回结构化 JSON 错误，并且不创建新 job。

## 原因

- 根因：`CrawlRunIn` 只校验请求体显式提供的 `date_from/date_to`，`create_jobs()` 在用上次成功 job 推导增量起点后没有再次校验最终日期范围。
- 影响范围：抓取增量调度、`crawl_jobs` 可追溯性、发布 smoke 之外的手动短窗口补抓。

## 修复

- 修改文件：`app/services/crawl.py`、`app/routers/crawl.py`、`tests/test_api.py`、`docs/接口设计文档.md`。
- 关键行为：`create_jobs()` 在插入 `crawl_jobs` 前校验最终 `start/date_to`；反向时抛出语义错误，router 返回 `400 invalid_crawl_date_range`，且不创建 pending job。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_run_rejects_derived_reversed_incremental_date_range -q` 失败，当前实现返回 `202`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_run_rejects_derived_reversed_incremental_date_range tests/test_api.py::test_crawl_run_rejects_invalid_period_and_reversed_dates tests/test_api.py::test_crawl_run_response_includes_created_job_context tests/test_api.py::test_crawl_run_rejects_partially_unknown_journal_ids_without_creating_jobs -q` 通过，`4 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_api.py -q -k "crawl_run or create_jobs or crawl_job"` 通过，`31 passed, 384 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`849 passed`。
