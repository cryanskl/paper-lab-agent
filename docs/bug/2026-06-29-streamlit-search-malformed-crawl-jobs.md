# Streamlit search page crashed on malformed crawl job items

## 现象

- 触发命令、接口或页面：Streamlit 搜索页调用 `/api/v1/crawl/jobs` 后，直接把 `crawl_jobs_response["items"]` 作为表格和任务详情下拉的数据源。
- 实际结果：任务详情下拉会用 `selected_job["id"]` 生成 `/crawl/jobs/{id}` 请求；当列表混入非对象、缺少 `id`、字符串 `id` 或 bool `id` 的条目时，页面会在渲染或请求详情时崩溃。
- 期望结果：进入抓取任务表格和详情下拉的 job 必须带有非 bool 整数 `id`；异常条目被跳过，分页和 total 仍照常显示。

## 原因

- 根因：抓取任务列表直接使用 `/crawl/jobs` 原始 items，没有在 UI 使用前做最小结构校验。
- 影响范围：搜索页抓取任务表格、任务详情下拉、任务详情 API 请求，以及异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `crawl_job_items()`，仅保留带非 bool 整数 `id` 的 job；搜索页抓取任务列表改为遍历过滤后的 `jobs`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_crawl_job_items_skip_malformed_items tests/test_api.py::test_streamlit_crawl_jobs_exposes_pagination_controls -q` 失败，helper 缺失且搜索页仍直接使用 `crawl_jobs_response["items"]`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_crawl_job_items_skip_malformed_items tests/test_api.py::test_streamlit_crawl_jobs_table_flattens_diagnostics tests/test_api.py::test_streamlit_crawl_job_detail_metrics_guard_malformed_diagnostics tests/test_api.py::test_streamlit_crawl_jobs_use_option_label_helper tests/test_api.py::test_streamlit_crawl_jobs_show_empty_state tests/test_api.py::test_streamlit_crawl_jobs_exposes_pagination_controls tests/test_api.py::test_streamlit_crawl_jobs_list_errors_show_payload_details tests/test_api.py::test_streamlit_crawl_job_detail_errors_show_payload_details -q` 通过，8 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1212 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1212 passed`。
