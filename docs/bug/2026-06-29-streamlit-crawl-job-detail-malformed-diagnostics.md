# Streamlit crawl job detail metrics crashed on malformed diagnostics

## 现象

- 触发命令、接口或页面：Streamlit 搜索页选择抓取任务详情后，会读取 `job_detail["diagnostics"]` 并渲染 found / filtered / accepted / new 指标。
- 实际结果：即使 `crawl_job_diagnostic_rows()` 已能处理 malformed diagnostics，页面指标区仍直接执行 `diagnostics.get(...)`；当 `diagnostics` 是字符串等非对象值时，页面会触发 `AttributeError`，无法继续展示详情表格和原始 JSON。
- 期望结果：页面指标区应与 helper 层一致，把无效 diagnostics 按空对象处理，继续展示零值指标、详情表格和原始响应。

## 原因

- 根因：Streamlit 页面中存在一处绕过前端 helper 的直接嵌套对象读取；此前修复覆盖了 `crawl_job_rows()` 和 `crawl_job_diagnostic_rows()`，但没有覆盖详情指标区。
- 影响范围：Streamlit 搜索页抓取任务详情、异常 API 响应或接口契约漂移下的抓取诊断回看流程。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：Streamlit 搜索页导入并使用 `dict_or_empty()` 读取 `job_detail.get("diagnostics")`，让详情指标区与 crawl job helper 使用相同对象 fallback。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_crawl_job_detail_metrics_guard_malformed_diagnostics -q` 失败，页面未导入 `dict_or_empty`，仍使用 `diagnostics = job_detail.get("diagnostics", {})`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_crawl_job_detail_metrics_guard_malformed_diagnostics tests/test_api.py::test_streamlit_crawl_jobs_table_flattens_diagnostics tests/test_api.py::test_streamlit_crawl_job_detail_errors_show_payload_details tests/test_frontend_api.py::test_crawl_job_diagnostic_rows_handle_malformed_nested_objects -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1194 passed`。
