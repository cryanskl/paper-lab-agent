# Frontend config warning display misreported malformed warning fields

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.config_warnings`，但单条 warning 的 `capability` 或 `message` 字段不是非空字符串，例如 `capability` 是列表或 `message` 是布尔值。
- 实际结果：`config_warning_rows()` 直接把异常字段强转成字符串，显示为 `['llm_translation']: True`，看起来像正常配置告警。
- 期望结果：`capability` 若存在必须是非空字符串，`message` 或 fallback `code` 必须是非空字符串；其他形状应显示 `config_warnings: invalid` 诊断行。

## 原因

- 根因：展示层 helper 只校验 warning 项是否为 dict，没有校验内部字段类型和值，导致异常 API 响应形状被格式化成正常配置告警文案。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的配置告警诊断。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`config_warning_rows()` 在渲染 warning 前校验 `capability`、`message` 或 `code` 的字符串形状；字段异常时输出 `{"capability": "config_warnings", "message": "invalid"}`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_config_warning_rows_blocks_malformed_config_warning_fields -q` 失败，列表和布尔值被展示为 `"['llm_translation']"` / `"True"`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_config_warning_rows_blocks_malformed_config_warning_fields tests/test_frontend_api.py::test_config_warning_rows_blocks_malformed_config_warning_objects -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`101 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_surfaces_config_warnings -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1158 passed`。
