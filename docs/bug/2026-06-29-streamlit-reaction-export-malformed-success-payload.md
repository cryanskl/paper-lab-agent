# Streamlit reaction export crashed on malformed success payload

## 现象

- 触发命令、接口或页面：Streamlit 化学库页点击“导出反应集”，`POST /reaction-sets/{id}/export` 返回成功后显示导出路径与下载按钮。
- 实际结果：当导出接口返回 2xx JSON 对象但缺少 `output_path`，或 `output_path` 类型异常时，成功分支直接索引 `payload["output_path"]` 并导致页面崩溃。
- 期望结果：导出成功分支能显示安全的成功状态；异常成功 payload 显示 `export path unavailable` 和明确 warning，不影响导出元数据表、下载可用性提示和 raw payload 展示。

## 原因

- 根因：化学库导出成功提示没有复用前端容错 helper，而是直接访问导出响应字段。
- 影响范围：化学库导出是阶段 4 交付链路出口；代理层、反向代理或 API 版本漂移导致 2xx 响应结构异常时，发布演示会在最终导出后中断。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `reaction_export_success_state()` 规范化导出成功 payload；Streamlit 导出成功分支改为渲染 `export_success["message"]`，异常字段显示 `reaction export response: invalid` warning。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_export_success_state_blocks_malformed_success_payloads tests/test_api.py::test_streamlit_chemistry_export_normalizes_success_payload -q` 失败，helper 不存在且 Streamlit 仍直接索引导出响应 `output_path`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_export_success_state_blocks_malformed_success_payloads tests/test_frontend_api.py::test_reaction_export_rows_summarize_download_and_audit_metadata tests/test_frontend_api.py::test_reaction_export_download_returns_none_for_missing_output_file tests/test_api.py::test_streamlit_chemistry_export_normalizes_success_payload tests/test_api.py::test_streamlit_chemistry_export_errors_show_payload_details tests/test_api.py::test_streamlit_chemistry_export_offers_download -q` 通过，6 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1245 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1245 passed。
