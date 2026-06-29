# Frontend workflow status display misreported malformed count values

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.status_counts`，但某个 workflow 的状态计数不是非负整数，例如 `{"failed": true}`。
- 实际结果：`status_count_rows()` 直接把异常值插入表格行，显示为 `failed=True`，看起来像正常 workflow 计数。
- 期望结果：状态名必须是非空字符串，计数必须是非 bool 的非负整数；其他形状应显示 `status=invalid,count=1` 的诊断行。

## 原因

- 根因：展示层 helper 只校验 workflow 计数桶是否为 dict，没有校验每个状态名和计数值，导致异常 API 响应形状被格式化成正常表格数据。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的 workflow 状态计数诊断。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`status_count_rows()` 展开 workflow 计数时校验状态名为非空字符串、计数为非 bool 的非负整数；异常项输出 `{"workflow": <name>, "status": "invalid", "count": 1}`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_status_count_rows_blocks_malformed_status_count_values -q` 失败，`{"failed": true}` 被展示为正常 `failed=True` 行。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_status_count_rows_blocks_malformed_status_count_values tests/test_frontend_api.py::test_status_count_rows_blocks_malformed_status_counts_objects -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`100 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_exposes_runtime_status -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1157 passed`。
