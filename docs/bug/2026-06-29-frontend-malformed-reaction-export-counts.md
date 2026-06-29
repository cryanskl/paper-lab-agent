# Frontend reaction export rows crashed on malformed count fields

## 现象

- 触发命令、接口或页面：Streamlit 化学页导出反应集后，使用 `/api/v1/reaction-sets/{id}/export` 返回项渲染 `reaction_export_rows()`；`reaction_count` 或 `audit_entry_count` 字段类型异常，例如返回列表或字符串。
- 实际结果：`reaction_export_rows()` 直接调用 `int(payload.get(...))`，`reaction_count` 为列表时抛出 `TypeError`，导致导出结果元数据表无法渲染。
- 期望结果：导出结果 helper 应使用稳定 fallback：异常计数字段显示 `0`，并继续生成下载 label 与导出元数据行。

## 原因

- 根因：展示层 helper 假设导出响应来自完整 API 契约，没有校验计数字段类型和值。
- 影响范围：Streamlit 化学页反应集导出结果表格、异常 API 响应或接口契约漂移时的导出下载流程。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`reaction_export_rows()` 对 `reaction_count` 和 `audit_entry_count` 使用非负整数校验和 `0` fallback，避免 malformed export response 触发崩溃。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_export_rows_handle_malformed_counts -q` 失败，`reaction_count` 为列表时触发 `TypeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_export_rows_handle_malformed_counts tests/test_frontend_api.py::test_reaction_export_rows_summarize_download_and_audit_metadata -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_export_surfaces_file_and_metadata_status -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`113 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1170 passed`。
