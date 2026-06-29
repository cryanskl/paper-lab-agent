# Streamlit search page crashed on malformed response envelope

## 现象

- 触发命令、接口或页面：Streamlit 搜索页完成 `/papers` 请求后渲染结果计数、分页和搜索卡片。
- 实际结果：当 `/papers` 返回 2xx JSON 对象但缺少 `items`、`total`、`page` 或 `page_size`，或这些字段类型异常时，页面会在直接索引响应字段时崩溃。
- 期望结果：搜索页在渲染前把响应 envelope 规范成 `{items,total,page,page_size}`；异常 envelope 显示为空结果，不影响页面继续渲染。

## 原因

- 根因：搜索页只校验了单条论文卡片字段，没有在使用 `papers["total"]`、`papers["page"]`、`papers["page_size"]` 和 `papers["items"]` 前校验列表响应 envelope。
- 影响范围：搜索页结果区、发布演示中的异常 API 响应处理，以及历史/代理层返回不完整 JSON 时的前端稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `paper_search_response_state()`，将异常响应规范为空结果；Streamlit 搜索页在渲染指标和列表前统一调用该 helper。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_search_response_state_handles_malformed_envelope tests/test_api.py::test_streamlit_search_results_normalize_response_envelope -q` 失败，helper 缺失且搜索页未规范化响应 envelope。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_search_response_state_handles_malformed_envelope tests/test_api.py::test_streamlit_search_results_normalize_response_envelope tests/test_api.py::test_streamlit_search_results_use_filtered_paper_items tests/test_api.py::test_streamlit_search_results_use_guarded_abstract_preview tests/test_api.py::test_streamlit_search_results_use_guarded_dedupe_label -q` 通过，5 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1224 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1224 passed。
