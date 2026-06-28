# Frontend paper upload selection crashed on malformed paper options

## 现象

- 触发命令、接口或页面：Streamlit 文档页上传 PDF 时从 `/papers` 读取 `items`，再用 `st.selectbox("关联论文", ..., format_func=paper_upload_option_label)` 展示可关联论文；papers 列表里混入非对象条目。
- 实际结果：`paper_upload_option_label()` 直接调用 `paper.get()`，非对象 paper 会触发 `AttributeError`；即使 label 降级，异常 paper 仍可能进入 `selected_upload_paper["id"]` 上传 payload 构造路径并崩溃。
- 期望结果：关联论文选择器应稳定降级：选项构建阶段跳过非对象 paper，label helper 对异常 paper 返回稳定占位，上传 payload 只会收到 `None` 或有效 paper 对象。

## 原因

- 根因：文档上传页直接用 `[None] + paper_upload_papers.get("items", [])` 构造 selectbox options，且 `paper_upload_option_label()` 假设每个 paper 都是 API 契约对象。
- 影响范围：PDF 导入入口、论文关联工作流、演示时搜索结果异常或接口契约漂移下的稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `paper_upload_options()`，返回 `[None]` 加有效 paper 对象，跳过非对象条目；`paper_upload_option_label()` 对非对象 paper 返回 `#- · Untitled · DOI: - · - · -`；Streamlit 使用该 helper 构造关联论文选项。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_upload_options_skip_malformed_papers tests/test_frontend_api.py::test_paper_upload_option_label_handles_malformed_paper -q` 失败，缺少 `paper_upload_options`，且非对象 paper 触发 `AttributeError: 'str' object has no attribute 'get'`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_document_upload_can_select_linked_paper -q` 失败，Streamlit 尚未使用 `paper_upload_options(paper_upload_papers.get("items", []))`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_upload_options_skip_malformed_papers tests/test_frontend_api.py::test_paper_upload_option_label_handles_malformed_paper tests/test_frontend_api.py::test_paper_upload_option_label_returns_unlinked_choice tests/test_frontend_api.py::test_paper_upload_option_label_summarizes_paper_identity tests/test_frontend_api.py::test_paper_upload_option_label_uses_sparse_fallbacks -q` 通过，`5 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_document_upload_can_select_linked_paper -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1186 passed`。
