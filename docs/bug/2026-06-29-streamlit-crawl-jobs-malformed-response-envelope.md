# Streamlit crawl jobs crashed on malformed response envelope

## 现象

- 触发命令、接口或页面：Streamlit 搜索页的抓取任务列表区完成 `/crawl/jobs` 请求后渲染分页、总数和任务表格。
- 实际结果：当 `/crawl/jobs` 返回 2xx JSON 对象但缺少 `items`、`total`、`page` 或 `page_size`，或这些字段类型异常时，页面会在直接索引响应字段时崩溃。
- 期望结果：抓取任务列表在渲染前把响应 envelope 规范成 `{items,total,page,page_size}`；异常 envelope 显示为空任务列表，不影响页面继续渲染。

## 原因

- 根因：抓取任务列表只过滤了单条 job item，没有在使用 `crawl_jobs_response["items"]`、`["page"]`、`["page_size"]` 和 `["total"]` 前校验列表响应 envelope。
- 影响范围：搜索页抓取任务区、发布演示中的异常 API 响应处理，以及历史/代理层返回不完整 JSON 时的前端稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `crawl_jobs_response_state()`，将异常响应规范为空任务列表；Streamlit 抓取任务区在渲染分页和表格前统一调用该 helper。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_crawl_jobs_response_state_handles_malformed_envelope tests/test_api.py::test_streamlit_crawl_jobs_normalize_response_envelope -q` 失败，helper 缺失且抓取任务区未规范化响应 envelope。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_crawl_jobs_response_state_handles_malformed_envelope tests/test_api.py::test_streamlit_crawl_jobs_normalize_response_envelope tests/test_api.py::test_streamlit_crawl_jobs_exposes_pagination_controls tests/test_api.py::test_streamlit_crawl_jobs_list_errors_show_payload_details tests/test_api.py::test_streamlit_crawl_jobs_show_empty_state -q` 通过，5 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1226 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1226 passed。
