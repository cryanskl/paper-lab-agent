# Streamlit config journals crashed on malformed response envelope

## 现象

- 触发命令、接口或页面：Streamlit 配置页加载 `/journals` 后渲染期刊白名单分页信息和期刊表格。
- 实际结果：当 `/journals` 返回 2xx JSON 对象但缺少 `items`、`total`、`page` 或 `page_size`，或这些字段类型异常时，配置页会在直接索引响应字段时崩溃。
- 期望结果：配置页在读取期刊列表字段前先规范化分页 envelope；异常 envelope 显示为空期刊列表，不影响配置页继续渲染。

## 原因

- 根因：配置页期刊白名单直接读取 `journals_response["items"]`、`["page"]`、`["page_size"]` 和 `["total"]`，没有复用已在其他列表页使用的响应 envelope 防护模式。
- 影响范围：期刊白名单管理、发布演示中的异常 API 响应处理，以及代理层返回不完整 JSON 时的前端稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：新增 `paginated_response_state()` 通用分页 envelope 规范化 helper；配置页在读取期刊列表字段前调用该 helper，并保留 `default_page_size=100`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_paginated_response_state_normalizes_malformed_envelope tests/test_api.py::test_streamlit_config_tab_normalizes_journals_response_envelope -q` 失败，通用分页规范化 helper 与配置页调用均不存在。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_paginated_response_state_normalizes_malformed_envelope tests/test_api.py::test_streamlit_config_tab_normalizes_journals_response_envelope tests/test_api.py::test_streamlit_config_tab_uses_filtered_journal_items tests/test_api.py::test_streamlit_config_tab_exposes_journal_pagination_controls tests/test_api.py::test_streamlit_config_metadata_errors_show_payload_details -q` 通过，5 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1232 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1232 passed。
