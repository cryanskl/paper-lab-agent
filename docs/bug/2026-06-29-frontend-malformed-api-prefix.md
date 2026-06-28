# Frontend runtime display misreported malformed API prefix

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.runtime.api_prefix`，但该字段不是非空字符串，例如列表 `["api"]`。
- 实际结果：`runtime_status_rows()` 直接把该值插入 caption，显示为 `API: ['api']`，看起来像正常运行时信息。
- 期望结果：`api_prefix` 只有非空字符串才应显示为 API 前缀；其他类型应显示 `api_prefix: invalid` warning，避免运行时诊断误报。

## 原因

- 根因：展示层 helper 对 `api_prefix` 使用 truthy fallback，没有校验类型，导致异常 API 响应形状被格式化成正常 caption。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的 API 前缀诊断。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`runtime_status_rows()` 仅在 `api_prefix` 是非空字符串时显示 `API: <prefix>`；其他类型或空字符串输出 `api_prefix: invalid` warning。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_api_prefix -q` 失败，列表 `["api"]` 被展示为 `API: ['api']`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_api_prefix tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_scheduler_enabled tests/test_frontend_api.py::test_runtime_status_rows_blocks_malformed_runtime_objects -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`97 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_exposes_runtime_status -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1154 passed`。
