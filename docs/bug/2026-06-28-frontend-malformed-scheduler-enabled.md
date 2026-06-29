# Frontend runtime display misreported malformed scheduler flag

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.runtime.scheduler_enabled`，但该字段不是布尔值，例如字符串 `"yes"`。
- 实际结果：`runtime_status_rows()` 使用 `bool(...)` 归一化该字段，字符串 `"yes"` 会被展示成 `scheduler_enabled: True`。
- 期望结果：`scheduler_enabled` 只有真实布尔值才能显示为启用 / 禁用；其他类型应显示 `scheduler_enabled: invalid` warning，避免运行时诊断误报。

## 原因

- 根因：展示层 helper 为了输出 caption 对任意值调用 `bool(...)`，把异常类型转换成 truthy / falsy 状态，丢失了 API 响应形状漂移信号。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的调度器状态诊断。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`runtime_status_rows()` 仅在 `scheduler_enabled` 是 `bool` 时显示 `scheduler_enabled: True/False`；其他类型输出 `scheduler_enabled: invalid` warning。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_scheduler_enabled -q` 失败，字符串 `"yes"` 被展示为 `scheduler_enabled: True`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_scheduler_enabled tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_runtime_objects -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`96 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_exposes_runtime_status -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1153 passed`。
