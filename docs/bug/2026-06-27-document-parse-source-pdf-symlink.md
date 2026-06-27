# Document parse followed symlinked source PDF files

## 现象

- 触发命令、接口或页面：`POST /api/v1/documents/{id}/parse` 解析 `documents.file_path` 指向 symlink PDF 的文档记录。
- 实际结果：解析流程会跟随 symlink；GROBID 上传或本地 fallback 会读取配置目录外的目标 PDF，并把文档标记为 `parsed`。
- 期望结果：解析入口必须拒绝 symlinked source PDF；遇到 symlink 或非普通文件路径时解析失败，不能读取配置路径外的文档内容。

## 原因

- 根因：`app/services/documents.py` 的 `parse_document()` 在调用 GROBID 或 `read_document_text()` 前没有校验 `documents.file_path`。
- 影响范围：手工导入、迁移数据或异常数据库记录触发解析时，后续 TEI、sections、翻译、RAG、化学抽取可能建立在目录外文件内容上。

## 修复

- 修改文件：`app/services/documents.py`、`tests/test_api.py`。
- 关键行为：解析任务进入 GROBID/fallback 前复用文档路径安全检查；源 PDF 不安全时直接写入 `parse_status='failed'` 和清晰 `parse_error`，并清理下游解析产物。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_parse_document_rejects_symlinked_source_pdf -q` 失败，当前实现返回 `parsed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_parse_document_rejects_symlinked_source_pdf tests/test_api.py::test_parse_document_rejects_symlinked_tei_storage_dir tests/test_api.py::test_parse_document_fallback_writes_valid_tei_xml tests/test_api.py::test_parse_document_records_grobid_fallback_reason -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `810 passed`。
