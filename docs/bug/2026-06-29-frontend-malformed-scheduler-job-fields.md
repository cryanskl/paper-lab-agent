# Frontend runtime display misreported malformed scheduler job fields

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.runtime.scheduler_jobs`，但单个 job 的展示字段不是非空字符串，例如 `period` 是列表或 `schedule` 是空字符串。
- 实际结果：`runtime_status_rows()` 直接把异常字段插入 caption，显示为 `- ['daily'] · crawl-daily ·  UTC`，看起来像正常调度任务信息。
- 期望结果：scheduler job 的 `period`、`id`、`schedule`、`timezone` 只有全为非空字符串时才显示为正常 caption；其他形状应显示 `scheduler_jobs: invalid` warning。

## 原因

- 根因：展示层 helper 只校验 scheduler job 是否为 dict，没有校验 job 内部字段类型和值，导致异常 API 响应形状被格式化成正常 caption。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的调度任务诊断。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`runtime_status_rows()` 在渲染 scheduler job 前校验 `period`、`id`、`schedule`、`timezone` 都是非空字符串；否则输出 `scheduler_jobs: invalid` warning。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_scheduler_job_fields -q` 失败，异常 job 被展示为 `- ['daily'] · crawl-daily ·  UTC`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_scheduler_job_fields tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_version tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_api_prefix tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_scheduler_enabled tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_runtime_objects -q` 通过，`5 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`99 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_exposes_runtime_status -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1156 passed`。
