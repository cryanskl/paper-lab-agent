# Streamlit startup crashed on malformed health success payload

## 现象

- 触发命令、接口或页面：Streamlit 启动时调用 `/health` 并渲染顶部服务状态。
- 实际结果：当 `/health` 返回 2xx JSON 对象但缺少 `service` 或 `status`，或字段类型异常时，启动区直接索引 `health["service"]` 和 `health["status"]`，页面在任意 tab 渲染前崩溃。
- 期望结果：启动区能把异常 health payload 显示为明确的 invalid 状态和 warning，不影响后续错误信息展示与页面渲染。

## 原因

- 根因：Streamlit 启动区没有复用前端容错 helper，而是直接访问 `/health` 响应字段。
- 影响范围：新机器、代理层、反向代理或 API 版本漂移导致 `/health` 2xx 响应结构异常时，发布演示页面无法进入主界面。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `health_display_state()` 规范化 health payload；Streamlit 启动区改为渲染 `health_display["caption"]`，异常字段显示 `health: invalid` warning。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_health_display_state_blocks_malformed_health_payloads tests/test_api.py::test_streamlit_startup_health_normalizes_success_payload -q` 失败，helper 不存在且 Streamlit 仍直接索引 health 字段。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_health_display_state_blocks_malformed_health_payloads tests/test_api.py::test_streamlit_startup_health_normalizes_success_payload tests/test_api.py::test_streamlit_startup_health_error_shows_payload_details -q` 通过，3 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1241 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1241 passed。
