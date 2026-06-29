# Streamlit upload page accepted malformed linked paper options

## 现象

- 触发命令、接口或页面：Streamlit 文档页调用 `/api/v1/papers` 搜索关联论文后，用 `paper_upload_options()` 生成“关联论文”下拉。
- 实际结果：上传下拉只过滤非对象，但会保留缺少 `id`、字符串 `id` 或 bool `id` 的 paper；用户选中这类对象上传时，页面会读取 `selected_upload_paper["id"]` 生成 `paper_id`，导致崩溃或提交非法关联。
- 期望结果：进入上传关联论文下拉的 paper 必须带有非 bool 整数 `id`；异常条目被跳过，“不关联论文”选项仍保留。

## 原因

- 根因：`paper_upload_options()` 只校验对象类型，没有校验上传路径必需的 `id` 字段。
- 影响范围：文档上传、论文关联选择，以及异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`paper_upload_options()` 现在只保留带非 bool 整数 `id` 的 paper，并继续保留首个 `None` 选项表示不关联论文。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_upload_options_skip_malformed_papers -q` 失败，helper 保留了缺 id、字符串 id 和 bool id 的 paper 对象。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_upload_options_skip_malformed_papers tests/test_frontend_api.py::test_paper_upload_option_label_returns_unlinked_choice tests/test_frontend_api.py::test_paper_upload_option_label_summarizes_paper_identity tests/test_frontend_api.py::test_paper_upload_option_label_uses_sparse_fallbacks tests/test_frontend_api.py::test_paper_upload_option_label_handles_malformed_paper tests/test_api.py::test_streamlit_document_upload_can_select_linked_paper tests/test_api.py::test_streamlit_document_upload_shows_error_payload_details tests/test_api.py::test_streamlit_document_upload_shows_duplicate_result -q` 通过，8 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1214 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1214 passed`。
