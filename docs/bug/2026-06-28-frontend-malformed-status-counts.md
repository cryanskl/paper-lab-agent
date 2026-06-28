# Frontend workflow status display crashed on malformed status counts

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.status_counts`，但该字段不是对象，或某个 workflow 的计数字段不是对象。
- 实际结果：侧边栏内联调用 `status_counts.get(...)` 和 `.items()`，会抛出 `AttributeError`，状态分布诊断无法显示。
- 期望结果：malformed `status_counts` 顶层对象或 workflow 计数字段应作为 `invalid` 行展示，而不是让侧边栏崩溃。

## 原因

- 根因：`streamlit_app.py` 直接在页面代码里展开 `status_counts`，假设顶层和每个 workflow 都是 dict，没有展示层类型防线。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的工作流状态诊断信号。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `status_count_rows()`；顶层非 dict 时返回 `status_counts/invalid` 行，workflow 计数字段非 dict 时返回 `<workflow>/invalid` 行，并让 Streamlit 侧边栏通过该 helper 渲染状态分布。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_status_count_rows_blocks_malformed_status_counts_objects tests/test_api.py::test_streamlit_sidebar_surfaces_workflow_status_counts -q` 失败，分别表现为 helper 缺失和 sidebar 仍内联展开 `status_counts`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_status_count_rows_blocks_malformed_status_counts_objects tests/test_api.py::test_streamlit_sidebar_surfaces_workflow_status_counts -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`90 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "streamlit_sidebar"` 通过，`12 passed, 554 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1145 passed`。
