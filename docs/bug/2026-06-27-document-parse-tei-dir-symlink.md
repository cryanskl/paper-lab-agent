# Document parse followed symlinked TEI storage directories

## 现象

- 触发命令、接口或页面：`POST /api/v1/documents/{id}/parse` 解析已上传 PDF，且 `PAPER_LAB_TEI_DIR` 指向 symlink 目录。
- 实际结果：解析 finalization 会跟随 symlink，把 `document-{id}.tei.xml` 写入配置目录树之外，并把文档标记为 `parsed`。
- 期望结果：TEI 存储路径本身和父目录链不能包含项目控制外的 symlink；遇到 symlinked TEI storage dir 时解析失败，不能写出目录外文件。

## 原因

- 根因：`app/services/documents.py` 的 `parse_document()` 在 `tei_path.write_text()` 前没有检查目标路径或父目录链是否安全。
- 影响范围：GROBID/本地 fallback 解析生成的 TEI artifact、后续章节入库、翻译/RAG/化学抽取链路的解析证据可信度。

## 修复

- 修改文件：`app/services/documents.py`、`tests/test_api.py`。
- 关键行为：写入 TEI 前复用文档存储路径安全检查；遇到 symlink 或非普通文件路径时解析 finalization 失败，文档状态写为 `failed`，且不写入 symlink 目标目录。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_parse_document_rejects_symlinked_tei_storage_dir -q` 失败，当前实现返回 `parsed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_parse_document_rejects_symlinked_tei_storage_dir tests/test_api.py::test_parse_document_fallback_writes_valid_tei_xml tests/test_api.py::test_parse_document_records_grobid_fallback_reason tests/test_api.py::test_parse_document_falls_back_when_grobid_returns_only_references -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `807 passed`。
