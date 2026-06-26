# Streamlit reaction review API errors did not show payload details

## 现象

- 触发页面：Streamlit Chemistry tab 的反应人工复核保存按钮。
- 实际结果：`api_put(f"/reactions/{reaction['id']}/verify", json=payload)` 返回 API 错误时，页面只显示 `format_error_payload(result, status_code)`，没有展示原始 payload。
- 期望结果：页面在显示格式化错误文本的同时展示 `result` JSON，便于定位复核失败的字段级错误、状态码和响应体。

## 原因

- 根因：复核保存失败分支只调用 `st.warning(...)`，遗漏了其他 Streamlit 错误路径已使用的 `st.json(...)`。
- 影响范围：化学库人工复核、导出前 verified 闸门、复核失败排障。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：反应复核保存失败时现在同时展示格式化错误和原始 `result` payload。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_review_errors_show_payload_details -q` 修复前失败，提示缺少 `st.json(result)`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_review_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k streamlit_chemistry -q` 通过，`16 passed, 364 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`698 passed`。
