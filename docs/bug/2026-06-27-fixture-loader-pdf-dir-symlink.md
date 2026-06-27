# Fixture loader followed symlinked PDF storage directories

## 现象

- 触发命令、接口或页面：调用 `load_fixture_documents()` 或 `scripts/import_fixtures.py` 导入 walking skeleton 文档，且 `PAPER_LAB_PDF_DIR` 指向 symlink 目录。
- 实际结果：fixture loader 会跟随 symlink，把 fixture PDF 写入配置目录树之外，并继续写入 `documents.file_path`。
- 期望结果：fixture PDF 存储路径本身和父目录链不能包含项目控制外的 symlink；遇到 symlinked PDF storage dir 时导入失败，不能写出目录外文件。

## 原因

- 根因：`app/fixture_loader.py` 的 `load_fixture_documents()` 在 `stored.write_bytes(content)` 前没有检查目标路径或父目录链是否安全。
- 影响范围：fixture 导入、demo 数据准备、release gate 的 walking skeleton 数据落盘路径可信度。

## 修复

- 修改文件：`app/fixture_loader.py`、`tests/test_api.py`。
- 关键行为：fixture PDF 写入前复用文档存储路径安全检查；遇到 symlink 或非普通文件路径时抛出清晰错误，且不写入 symlink 目标目录。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_fixture_loader_rejects_symlinked_pdf_storage_dir -q` 失败，当前实现未抛错。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_fixture_loader_rejects_symlinked_pdf_storage_dir tests/test_api.py::test_fixture_loader_imports_idempotent_document_sample tests/test_api.py::test_fixture_import_script_runs_from_repo_root tests/test_api.py::test_prepare_demo_data_script_populates_walking_skeleton -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `808 passed`。
