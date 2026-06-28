# Streamlit document status dataframe Arrow warning

## 现象

- 触发命令、接口或页面：`PYTHON=.venv/bin/python API_PORT=61301 STREAMLIT_PORT=61302 PAPER_LAB_SCHEDULER_ENABLED=false bash scripts/dev.sh` 启动后，在浏览器打开 Streamlit 并进入“文档”页。
- 实际结果：终端输出 `Serialization of dataframe to Arrow table was unsuccessful`，原因是 `value` 列同时包含字符串和数字。
- 期望结果：文档状态表作为 UI 展示数据，应使用稳定的显示类型，不在发布演示时产生 Streamlit Arrow 自动修正 warning。

## 原因

- 根因：`streamlit_app.py` 直接把 `document_status_rows(document_detail, chunks)` 传给 `st.dataframe`；该 helper 的 `value` 列保留原始类型，包含 `document_id`、`chunks_total` 等整数和状态/错误字符串。
- 影响范围：Streamlit 文档页的状态表展示；不影响 API 响应或数据库，但会污染本地演示和浏览器验证日志。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `dataframe_display_rows()`，仅在 Streamlit 展示层把 `{field,value}` 行的 `value` 统一转成字符串；原始状态 helper 继续保留 API/测试可用的原始类型。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py -k "dataframe_display_rows" -q` 失败，当前实现缺少 `dataframe_display_rows`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py -k "dataframe_display_rows or paper_upload_option_label" && .venv/bin/python -m pytest tests/test_api.py -k "streamlit_document_upload_can_select_linked_paper or streamlit_documents_tab_exposes_preview_and_index_status"` 通过，`5 passed` 和 `2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1069 passed`。
