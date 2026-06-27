# Document upload followed symlinked PDF storage directories

## 现象

- 触发命令、接口或页面：`POST /api/v1/documents` 上传 PDF，且 `PAPER_LAB_PDF_DIR` 指向 symlink 目录。
- 实际结果：上传流程会跟随 symlink，把原始 PDF 写入配置目录树之外，并返回 `201 Created`。
- 期望结果：PDF 存储路径本身和父目录链不能包含项目控制外的 symlink；遇到 symlinked PDF storage dir 时上传失败，不能写出目录外文件。

## 原因

- 根因：`app/services/documents.py` 的 `save_upload()` 在 `stored.write_bytes(content)` 前没有检查目标路径或父目录链是否安全。
- 影响范围：PDF 上传、原始文档存储、后续解析/翻译/RAG/化学抽取链路的输入可信度。

## 修复

- 修改文件：`app/services/documents.py`、`app/routers/documents.py`、`tests/test_api.py`。
- 关键行为：写入 PDF 前扫描目标路径和父目录链；遇到 symlink 或非普通文件路径时抛出清晰错误，API 返回结构化 `document_upload_failed`，且不写入 symlink 目标目录。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_document_upload_rejects_symlinked_pdf_storage_dir -q` 失败，当前实现返回 `201`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_document_upload_rejects_symlinked_pdf_storage_dir tests/test_api.py::test_document_upload_records_pdf_page_count tests/test_api.py::test_document_upload_stores_pdf_with_pdf_extension_even_when_filename_is_misleading tests/test_api.py::test_duplicate_document_upload_returns_existing_resource -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `806 passed`。
