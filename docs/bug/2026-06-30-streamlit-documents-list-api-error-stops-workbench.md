# Streamlit documents list API error stopped the workbench

## 现象

- 触发命令、接口或页面：Streamlit 文档页、RAG 页或化学库页加载 `/documents` 文档列表时，后端返回结构化错误响应。
- 实际结果：页面把局部文档列表错误当作致命错误处理，导致工作台渲染被中断；RAG 提问区和化学库复核区也无法继续使用已有状态。
- 期望结果：文档列表失败时显示格式化错误和 raw payload，同时降级为空文档列表；页面其它区域继续渲染，用户可以继续使用不依赖该列表的操作。

## 原因

- 根因：三个面板的 `/documents` 异常处理路径沿用了启动健康检查式的致命处理，没有为局部列表加载失败构造可规范化的空分页 envelope。
- 影响范围：文档导入/预览、RAG 范围选择、化学库复核入口，以及演示时短暂 API 异常后的前端稳定性。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：`render_documents_panel()`、`render_rag_panel()`、`render_chemistry_panel()` 在 `/documents` 抛出 `FrontendApiError` 时展示 warning 和 raw payload，并构造 `{items,total,page,page_size}` 空 envelope 继续走现有 normalization/render 流程；文档详情错误同样保留页面渲染，不再调用 `st.stop()`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_export_errors_show_payload_details -q` 失败，旧测试仍绑定过期导出 id 变量，说明当前前端变更未形成可提交测试契约。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_documents_list_errors_show_payload_details tests/test_api.py::test_streamlit_document_detail_errors_show_payload_details tests/test_api.py::test_streamlit_rag_documents_list_errors_show_payload_details tests/test_api.py::test_streamlit_chemistry_documents_list_errors_show_payload_details tests/test_api.py::test_streamlit_chemistry_review_ui_exposes_review_fields tests/test_api.py::test_streamlit_chemistry_selected_document_clears_stale_reaction_set_detail tests/test_api.py::test_streamlit_chemistry_export_errors_show_payload_details -q` 通过，7 passed。
- Focused checks：`.venv/bin/python -m py_compile streamlit_app.py tests/test_api.py`、`.venv/bin/python -m pytest tests/test_api.py -k 'streamlit_' -q`、`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过。
