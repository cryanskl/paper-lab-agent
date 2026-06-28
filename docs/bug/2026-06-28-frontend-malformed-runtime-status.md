# Frontend runtime status display crashed on malformed runtime

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.runtime`，但 `runtime` 不是对象，或 `scheduler_jobs` 不是列表 / 列表内包含非对象元素。
- 实际结果：侧边栏直接调用 `runtime.get(...)`，并在 `for job in scheduler_jobs` 中直接调用 `job.get(...)`；异常形状会抛出 `AttributeError`，API 前缀、版本、调度器信息和后续诊断无法继续显示。
- 期望结果：malformed runtime 或 scheduler job 应显示为 `runtime: invalid` / `scheduler_jobs: invalid` warning，而不是中断侧边栏诊断。

## 原因

- 根因：`streamlit_app.py` 直接展开 `/system/status.runtime`，没有像 release readiness、counts、storage health 一样通过展示层 helper 做类型防线。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的运行时状态和后续诊断信号。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `runtime_status_rows()`；顶层非 dict 时输出 `runtime: invalid` warning，`scheduler_jobs` 形状异常时输出 `scheduler_jobs: invalid` warning；Streamlit 侧边栏改为按 helper 返回的 caption/warning 行渲染。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_runtime_objects tests/test_api.py::test_streamlit_sidebar_exposes_runtime_status -q` 失败，分别表现为 helper 缺失和 sidebar 仍未使用 runtime 展示 helper。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_runtime_objects tests/test_api.py::test_streamlit_sidebar_exposes_runtime_status -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`94 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_exposes_runtime_status tests/test_api.py::test_streamlit_sidebar_uses_safe_system_count_metrics tests/test_api.py::test_streamlit_sidebar_links_live_api_documentation -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1150 passed`。
