# Frontend crawl job rows crashed on malformed diagnostics counts

## 现象

- 触发命令、接口或页面：Streamlit 搜索页的抓取任务表格使用 `/api/v1/crawl/jobs` 返回项渲染 `crawl_job_rows()`；单个 crawl job 的 `diagnostics.papers_found`、`papers_filtered`、`papers_accepted`、`papers_existing`、`papers_new` 或 `keyword_terms` 字段类型异常，例如计数字段是列表或字符串，`keyword_terms` 是对象。
- 实际结果：`crawl_job_rows()` 直接调用 `int(diagnostics.get(...))`，计数字段为列表时抛出 `TypeError`；`keyword_terms` 非列表时也可能导致误展示或拼接异常。
- 期望结果：表格行 helper 应使用稳定 fallback：异常计数字段显示 `0`，异常 `keyword_terms` 显示空字符串，并继续生成 `progress_summary` 与工作流状态。

## 原因

- 根因：展示层 helper 假设 crawl job diagnostics 来自完整 API 契约，没有校验字段类型和值。
- 影响范围：Streamlit 搜索页抓取任务表格、异常 API 响应或接口契约漂移时的抓取任务回看流程。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`crawl_job_rows()` 对 diagnostics 计数字段使用非负整数校验和 `0` fallback，对 `keyword_terms` 使用列表校验，避免 malformed crawl job item 触发崩溃或误展示。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_crawl_job_rows_handle_malformed_diagnostics_counts -q` 失败，`papers_found` 为列表时触发 `TypeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_crawl_job_rows_handle_malformed_diagnostics_counts tests/test_frontend_api.py::test_crawl_job_rows_summarize_diagnostics_and_workflow_state -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_crawl_jobs_table_flattens_diagnostics -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`110 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1167 passed`。
