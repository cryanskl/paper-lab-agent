# Streamlit category create crashed on malformed success payload

## 现象

- 触发命令、接口或页面：Streamlit 配置页提交“新增分类”，`POST /categories` 返回 201 后显示新增结果。
- 实际结果：当 `/categories` 返回 201 JSON 对象但缺少 `id`，或 `id` 类型异常时，成功分支直接索引 `result["id"]` 并导致页面崩溃。
- 期望结果：新增分类成功分支能显示安全的成功状态；异常成功 payload 显示 `category #unknown` 和明确 warning，不影响配置页继续渲染。

## 原因

- 根因：新增分类成功提示直接访问创建响应字段，没有对 201 payload 做前端容错规范化。
- 影响范围：分类配置是检索、人工分类和 RAG 筛选的基础配置；代理层、反向代理或 API 版本漂移导致 201 响应结构异常时，配置页会在新增分类后中断。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `category_create_success_state()` 规范化新增分类成功 payload；Streamlit 新增分类成功分支改为渲染 `category_success["message"]`，异常字段显示 `category create response: invalid` warning。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_category_create_success_state_blocks_malformed_success_payloads tests/test_api.py::test_streamlit_config_create_category_normalizes_success_payload -q` 失败，helper 不存在且 Streamlit 仍未接入新增分类成功 payload 规范化。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_category_create_success_state_blocks_malformed_success_payloads tests/test_frontend_api.py::test_journal_create_success_state_blocks_malformed_success_payloads tests/test_api.py::test_streamlit_config_create_category_normalizes_success_payload tests/test_api.py::test_streamlit_config_create_journal_normalizes_success_payload tests/test_api.py::test_streamlit_config_create_errors_show_payload_details -q` 通过，5 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1249 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1249 passed。
