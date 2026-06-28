# Frontend crawl job rows crashed on malformed nested objects

## 现象

- 触发命令、接口或页面：Streamlit 搜索页加载抓取任务列表和抓取任务详情时，`crawl_job_rows()` 与 `crawl_job_diagnostic_rows()` 会读取 crawl job 的 `diagnostics` 和 `journal` 嵌套对象。
- 实际结果：当 `diagnostics` 或 `journal` 因接口漂移、历史脏数据或异常响应变成字符串等非对象值时，helper 继续调用 `.get(...)`，触发 `AttributeError`，导致抓取任务表格或详情面板无法展示。
- 期望结果：前端展示层应稳定降级：无效嵌套对象按空对象处理，继续展示 job 自身的 `status`、`error`、`journal_id` 和零值统计。

## 原因

- 根因：此前只校验了 diagnostics 内部计数字段和 `keyword_terms` 的类型，没有保护 `diagnostics` / `journal` 自身的对象边界。
- 影响范围：Streamlit 搜索页抓取任务列表、抓取任务详情、异常 API 响应或接口契约漂移下的抓取诊断回看流程。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：新增 `dict_or_empty()`，`crawl_job_rows()` 和 `crawl_job_diagnostic_rows()` 读取 `diagnostics` / `journal` 前统一做对象 fallback，避免非对象嵌套字段进入 `.get(...)` 调用。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_crawl_job_rows_handle_malformed_nested_objects tests/test_frontend_api.py::test_crawl_job_diagnostic_rows_handle_malformed_nested_objects -q` 失败，两个 helper 都在非对象 `diagnostics` 上触发 `AttributeError: 'str' object has no attribute 'get'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_crawl_job_rows_handle_malformed_nested_objects tests/test_frontend_api.py::test_crawl_job_diagnostic_rows_handle_malformed_nested_objects tests/test_frontend_api.py::test_crawl_job_rows_handle_malformed_diagnostics_counts tests/test_frontend_api.py::test_crawl_job_diagnostic_rows_handle_malformed_counts tests/test_frontend_api.py::test_crawl_job_rows_summarize_diagnostics_and_workflow_state tests/test_frontend_api.py::test_crawl_job_diagnostic_rows_flatten_job_detail_for_review -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1193 passed`。
