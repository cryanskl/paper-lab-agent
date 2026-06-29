# Frontend external capabilities display crashed on malformed object

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.external_capabilities`，但该字段不是对象，或其中的 `grobid` 字段不是对象。
- 实际结果：侧边栏直接调用 `external_capabilities.get(...)` 或 `grobid.get(...)`，会抛出 `AttributeError`，外部能力诊断无法显示。
- 期望结果：malformed 外部能力对象应作为 warning 展示，而不是让侧边栏崩溃。

## 原因

- 根因：`streamlit_app.py` 只用 `status.get("external_capabilities", {})` 处理缺失字段；非空 list/string 会原样进入 `.get()` 调用。嵌套的 `grobid` 字段也缺少类型防线。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的外部能力诊断信号。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `external_capabilities_display_state()`；顶层非 dict 时返回 `external_capabilities:invalid` warning，嵌套 `grobid` 非 dict 时返回 `grobid:invalid` warning，并让 Streamlit 侧边栏通过该 helper 渲染外部能力状态。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_external_capabilities_display_state_blocks_malformed_objects tests/test_api.py::test_streamlit_sidebar_exposes_external_capability_status -q` 失败，分别表现为 helper 缺失和 sidebar 未使用 `external_capabilities_display_state`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_external_capabilities_display_state_blocks_malformed_objects tests/test_api.py::test_streamlit_sidebar_exposes_external_capability_status -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`89 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "streamlit_sidebar"` 通过，`12 passed, 554 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1144 passed`。
