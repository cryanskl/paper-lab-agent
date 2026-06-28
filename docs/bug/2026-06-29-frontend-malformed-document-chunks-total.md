# Frontend document status rows crashed on malformed chunks total

## 现象

- 触发命令、接口或页面：Streamlit 文档详情页使用 `/api/v1/documents/{id}/chunks` 返回项渲染 `document_status_rows()`；`chunks.total` 字段类型异常，例如返回列表或字符串。
- 实际结果：`document_status_rows()` 直接调用 `int(chunks.get("total"))`，`total` 为列表时抛出 `TypeError`，导致文档详情状态表无法渲染。
- 期望结果：状态行 helper 应使用稳定 fallback：异常 `chunks.total` 显示 `0`，并继续显示解析、索引、化学抽取状态。

## 原因

- 根因：展示层 helper 假设 chunks 分页响应来自完整 API 契约，没有校验 `total` 字段类型和值。
- 影响范围：Streamlit 文档详情页状态表、异常 API 响应或接口契约漂移时的文档查看与索引状态回看流程。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`document_status_rows()` 对 `chunks.total` 使用非负整数校验和 `0` fallback，避免 malformed chunks response 触发崩溃。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_status_rows_handle_malformed_chunks_total -q` 失败，`chunks.total` 为列表时触发 `TypeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_status_rows_handle_malformed_chunks_total tests/test_frontend_api.py::test_document_status_rows_summarize_document_workflow_and_errors -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_documents_tab_exposes_preview_and_index_status -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`112 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1169 passed`。
