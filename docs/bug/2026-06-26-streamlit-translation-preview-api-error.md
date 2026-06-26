# Streamlit translation preview API errors were not surfaced

## 现象

- 触发页面：Streamlit Documents tab 的翻译预览区域。
- 实际结果：`api_get(f"/documents/{selected['id']}/translation")` 如果返回 API 错误，会被泛用 `Exception` 分支处理，只显示 `translation_preview unavailable: ...`，没有展示统一错误文本和原始 payload。
- 期望结果：页面显示 `format_error_payload(exc.payload, exc.status_code)`，同时展示 `exc.payload`，便于定位翻译预览接口的真实错误码和响应体。

## 原因

- 根因：翻译预览加载没有 `FrontendApiError` 专用处理分支，结构化 API payload 被泛用异常文案吞掉。
- 影响范围：翻译预览、翻译任务排障、文档理解链路演示。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：翻译预览加载现在优先捕获 `FrontendApiError`，显示格式化错误和原始 payload；非 API 异常仍保留原有兜底提示。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_translation_preview_errors_show_payload_details -q` 修复前失败，提示缺少 `except FrontendApiError as exc:`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_translation_preview_errors_show_payload_details -q` 通过；`.venv/bin/python -m pytest tests/test_api.py -k "streamlit_documents or streamlit_document or streamlit_translation" -q` 通过，`22 passed, 357 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`697 passed`。
