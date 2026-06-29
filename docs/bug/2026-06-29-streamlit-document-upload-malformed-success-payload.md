# Streamlit document upload crashed on malformed success payload

## 现象

- 触发命令、接口或页面：Streamlit 文档页上传 PDF，`POST /documents` 返回 201 后显示上传结果。
- 实际结果：当 `/documents` 返回 201 JSON 对象但缺少 `id`，或 `id` 类型异常时，上传成功分支直接索引 `payload["id"]` 并导致页面崩溃。
- 期望结果：上传成功分支能显示安全的成功状态；异常成功 payload 显示 `document #unknown` 和明确 warning，不影响文档页继续渲染。

## 原因

- 根因：文档上传成功分支没有复用前端容错 helper，而是直接访问上传响应字段。
- 影响范围：上传 PDF 是理解链路 walking skeleton 的入口；代理层、反向代理或 API 版本漂移导致 201 响应结构异常时，发布演示会在导入文档后中断。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `document_upload_success_state()` 规范化上传成功 payload；Streamlit 上传成功分支改为渲染 `upload_success["message"]`，异常字段显示 `document upload response: invalid` warning。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_upload_success_state_blocks_malformed_success_payloads tests/test_api.py::test_streamlit_document_upload_normalizes_success_payload -q` 失败，helper 不存在且 Streamlit 仍直接索引上传响应 `id`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_upload_success_state_blocks_malformed_success_payloads tests/test_api.py::test_streamlit_document_upload_normalizes_success_payload tests/test_api.py::test_streamlit_document_upload_shows_duplicate_result tests/test_api.py::test_streamlit_document_upload_shows_error_payload_details -q` 通过，4 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1243 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1243 passed。
