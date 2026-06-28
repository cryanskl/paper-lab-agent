# Frontend translation preview crashed on malformed preview text

## 现象

- 触发命令、接口或页面：Streamlit 文档页的“翻译预览”tab 调用 `translation_status_rows(translation_preview, preview_text=...)` 展示翻译状态和文件预览；预览文本参数不是字符串，例如列表或对象。
- 实际结果：`translation_status_rows()` 将异常预览值直接传给 `summarize_text()`，后者调用 `.split()` 时触发 `AttributeError`，导致翻译预览页渲染失败。
- 期望结果：翻译状态展示层应稳定降级：异常预览显示 `preview=invalid`、`preview_chars=0`，状态、错误信息和路径等其它字段继续展示。

## 原因

- 根因：展示层 helper 假设翻译预览内容一定是字符串，没有在 Streamlit 渲染边界校验 `preview_text` 类型。
- 影响范围：Streamlit 文档页翻译预览、翻译失败排障，以及文件读取/接口契约漂移时的演示稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`translation_status_rows()` 只有在 `preview_text` 为字符串或 `None` 时计算字符数并摘要；其它类型显示 `invalid`，不影响翻译状态表的其余字段。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_translation_status_rows_handle_malformed_preview_text -q` 失败，异常预览值触发 `AttributeError: 'list' object has no attribute 'split'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_translation_status_rows_handle_malformed_preview_text tests/test_frontend_api.py::test_translation_status_rows_summarize_output_file_preview -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`117 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_translation_preview_shows_failed_status tests/test_api.py::test_streamlit_translation_preview_offers_download tests/test_api.py::test_streamlit_translation_preview_errors_show_payload_details tests/test_api.py::test_streamlit_translation_preview_warns_when_output_file_is_missing -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1174 passed`。
