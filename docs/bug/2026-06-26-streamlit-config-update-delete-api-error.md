# Streamlit config update and delete API errors did not show payload details

## 现象

- 触发页面：Streamlit 配置 tab 的“更新期刊”和“停用期刊”按钮。
- 实际结果：`api_put(f"/journals/{selected_journal['id']}", ...)` 或 `api_delete(f"/journals/{selected_journal['id']}")` 返回 API 错误时，页面只显示 `format_error_payload(result, status_code)`，没有展示原始 payload。
- 期望结果：页面在显示格式化错误文本的同时展示 `result` JSON，便于定位期刊更新或停用失败的错误码、message 和后端响应体。

## 原因

- 根因：配置页更新/停用期刊失败分支只调用 `st.warning(...)`，遗漏了其他 Streamlit 错误路径已使用的 `st.json(...)`。
- 影响范围：发布演示、期刊白名单维护、排查表单校验或资源不存在等 API 错误。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：更新期刊和停用期刊失败时现在同时展示格式化错误和原始 `result` payload。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_update_delete_errors_show_payload_details -q` 修复前失败，提示缺少 `st.json(result)`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_update_delete_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k streamlit_config -q` 通过，`10 passed, 376 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`704 passed`。
