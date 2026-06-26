# Streamlit config create API errors did not show payload details

## 现象

- 触发页面：Streamlit 配置 tab 的“新增期刊”和“新增分类”表单。
- 实际结果：`api_post("/journals", ...)` 或 `api_post("/categories", ...)` 返回 API 错误时，页面只显示 `format_error_payload(result, status_code)`，没有展示原始 payload。
- 期望结果：页面在显示格式化错误文本的同时展示 `result` JSON，便于定位创建失败的错误码、message 和后端响应体。

## 原因

- 根因：配置页创建资源失败分支只调用 `st.warning(...)`，遗漏了其他 Streamlit 错误路径已使用的 `st.json(...)`。
- 影响范围：发布演示、配置白名单期刊、维护分类 taxonomy、排查表单校验或唯一约束错误。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：新增期刊和新增分类失败时现在同时展示格式化错误和原始 `result` payload。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_create_errors_show_payload_details -q` 修复前失败，提示缺少 `st.json(result)`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_config_create_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k streamlit_config -q` 通过，`9 passed, 376 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`703 passed`。
