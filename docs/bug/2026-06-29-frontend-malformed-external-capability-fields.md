# Frontend external capability display misreported malformed fields

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.external_capabilities`，但外部能力字段类型异常，例如 `openalex_mailto` 是字符串 `"yes"` 或 `translation_adapter` 是列表。
- 实际结果：`external_capabilities_display_state()` 原样透传异常字段，侧边栏会把非空字符串当成已配置，或把列表展示成正常 adapter 值。
- 期望结果：布尔能力字段必须是布尔值，字符串能力字段必须是字符串；其他形状应显示 `external_capabilities:invalid` warning，并降级为前端安全的未配置或空值。

## 原因

- 根因：展示层 helper 只校验 `external_capabilities` 顶层对象和 `grobid` 对象形状，没有校验外部能力字段类型，导致异常 API 响应形状被当成正常配置状态。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的外部能力配置诊断。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`external_capabilities_display_state()` 校验 `openalex_mailto`、`unpaywall_email`、`llm_api_key` 为布尔值，校验 `grobid_url`、`translation_adapter`、`llm_model`、`embedding_model`、`vector_db_backend` 为字符串；异常字段输出 `external_capabilities:invalid` warning，并在返回给 sidebar 的 `capabilities` 中降级为 `False` 或空字符串。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_external_capabilities_display_state_blocks_malformed_capability_fields -q` 失败，malformed capability 没有 warning 且被原样透传。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_external_capabilities_display_state_blocks_malformed_capability_fields tests/test_frontend_api.py::test_external_capabilities_display_state_blocks_malformed_objects -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`103 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_exposes_external_capability_status -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1160 passed`。
