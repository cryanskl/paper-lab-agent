# Streamlit crawl job detail API errors were not surfaced

## 现象

- 触发页面：Streamlit 检索 tab 的抓取任务详情区域。
- 实际结果：`api_get(f"/crawl/jobs/{selected_job['id']}")` 如果返回 API 错误，会抛出 `FrontendApiError`，页面没有展示统一错误文本和原始 payload。
- 期望结果：页面显示 `format_error_payload(exc.payload, exc.status_code)`，同时展示 `exc.payload`，并跳过依赖 `job_detail` 的诊断指标、诊断表和 JSON 详情渲染。

## 原因

- 根因：任务详情加载沿用了裸 `api_get`，没有 `FrontendApiError` 专用处理分支。
- 影响范围：抓取任务详情、crawl job 诊断、确定性检索层演示和 API 排障。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：抓取任务详情加载现在捕获 `FrontendApiError`，显示格式化错误和原始 payload，并只在 `job_detail` 存在时渲染后续诊断内容。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_crawl_job_detail_errors_show_payload_details -q` 修复前失败，提示缺少 `except FrontendApiError as exc:`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_crawl_job_detail_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k "streamlit_crawl or streamlit_search" -q` 通过，`16 passed, 359 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`693 passed`。
