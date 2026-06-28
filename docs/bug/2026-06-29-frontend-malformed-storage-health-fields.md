# Frontend storage health display misreported malformed health fields

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.storage_health`，但单个存储健康项的字段类型异常，例如 `path` 是列表或 `exists` 是字符串。
- 实际结果：`storage_health_caption_rows()` 直接按 truthy 规则展示，显示为 `data_dir: exists · writable · ['data']`，看起来像正常存储健康信息。
- 期望结果：存储健康项中已提供的 `path` 必须是字符串，`exists`、`writable`、`valid_json` 必须是布尔值，`error` 必须是字符串；字段异常时应显示 `<key>: invalid` warning。

## 原因

- 根因：展示层 helper 只校验存储健康项是否为 dict，没有校验内部字段类型，导致异常 API 响应形状被格式化成正常 caption。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的存储健康诊断。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`storage_health_caption_rows()` 在渲染存储健康项前校验已提供字段的类型；字段异常时输出 `<key>: invalid` warning，并避免把异常值展示成正常路径或状态。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_storage_health_caption_rows_blocks_malformed_storage_health_fields -q` 失败，异常字段被展示为 `data_dir: exists · writable · ['data']`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_storage_health_caption_rows_blocks_malformed_storage_health_fields tests/test_frontend_api.py::test_storage_health_caption_rows_blocks_malformed_storage_health_entries tests/test_frontend_api.py::test_storage_health_caption_rows_include_parent_dirs_and_vector_json_state -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`102 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_surfaces_storage_health -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1159 passed`。
