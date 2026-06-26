# Streamlit chemistry export API errors did not show payload details

## 现象

- 触发页面：Streamlit 化学库 tab 的“导出反应集”按钮。
- 实际结果：`api_post(f"/reaction-sets/{rs_id}/export?format={export_format}", ...)` 返回 409 或其他 API 错误时，页面只显示 `format_error_payload(payload, status)`，没有展示原始 payload。
- 期望结果：页面在显示格式化错误文本的同时展示 `payload` JSON，便于定位未复核禁止导出、不支持导出格式或后端导出失败的错误码、message 和响应体。

## 原因

- 根因：化学库导出失败分支只调用 `st.warning(...)` 或 `st.error(...)`，遗漏了其他 Streamlit 错误路径已使用的 `st.json(...)`。
- 影响范围：发布演示、化学库复核闸门排障、导出格式或文件写入错误定位。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：反应集导出返回 409 或其他错误状态时，现在同时展示格式化错误和原始 `payload` JSON。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_export_errors_show_payload_details -q` 修复前失败，提示缺少 `st.json(payload)`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_export_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k streamlit_chemistry -q` 通过，`17 passed, 370 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`705 passed`。
