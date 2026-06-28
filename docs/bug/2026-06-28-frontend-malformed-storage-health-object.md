# Frontend storage health display crashed on malformed object

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.storage_health`，但该字段不是对象而是非空列表或字符串。
- 实际结果：`storage_health_caption_rows()` 直接调用 `.get()`，侧边栏会抛出 `AttributeError`，存储健康诊断无法显示。
- 期望结果：malformed `storage_health` 顶层对象应作为 warning row 展示，而不是让侧边栏崩溃。

## 原因

- 根因：`streamlit_app.py` 已将存储健康渲染委托给 `app/frontend_api.py` 的 `storage_health_caption_rows()`，但该 helper 假设输入一定是 dict。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的存储健康诊断信号。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`storage_health_caption_rows()` 现在先校验 `storage_health` 顶层对象；非 dict 时返回 `{"kind": "warning", "text": "storage_health: invalid"}`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_storage_health_caption_rows_blocks_malformed_storage_health_object -q` 失败，错误为 `AttributeError: 'list' object has no attribute 'get'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_storage_health_caption_rows_blocks_malformed_storage_health_object tests/test_frontend_api.py::test_storage_health_caption_rows_include_parent_dirs_and_vector_json_state -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`88 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1143 passed`。
