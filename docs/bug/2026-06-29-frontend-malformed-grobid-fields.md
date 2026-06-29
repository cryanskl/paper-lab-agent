# Frontend GROBID status display misreported malformed fields

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.external_capabilities.grobid`，但 GROBID 探测字段类型异常，例如 `available` 是字符串、`status_code` 是字符串或 `error` 是列表。
- 实际结果：`external_capabilities_display_state()` 原样透传异常 GROBID 字段，侧边栏会把这些值展示成正常 live status、status code 或 error 文案。
- 期望结果：GROBID 的 `url` 必须是字符串，`available` 必须是布尔值或空值，`status_code` 必须是非 bool 整数或空值，`error` 必须是字符串或空值；其他形状应显示 `grobid:invalid` warning，并避免误展示。

## 原因

- 根因：展示层 helper 只校验 `grobid` 是否为 dict，没有校验内部字段类型，导致异常 API 响应形状被当成正常 GROBID 探测结果。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的 GROBID live status 诊断。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`external_capabilities_display_state()` 在返回 GROBID 状态前校验 `url`、`available`、`status_code`、`error` 的类型；字段异常时输出 `grobid:invalid` warning，并返回空 GROBID 状态。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_external_capabilities_display_state_blocks_malformed_grobid_fields -q` 失败，malformed GROBID 字段没有 warning 且被原样透传。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_external_capabilities_display_state_blocks_malformed_grobid_fields tests/test_frontend_api.py::test_external_capabilities_display_state_blocks_malformed_capability_fields tests/test_frontend_api.py::test_external_capabilities_display_state_blocks_malformed_objects -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`104 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_can_check_grobid_live_status -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1161 passed`。
