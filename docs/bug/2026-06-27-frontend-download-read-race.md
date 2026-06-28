# 前端下载文件读取失败会打断页面

## 现象

Streamlit 下载 helper 在 `is_safe_download_file()` 判断文件可下载后直接读取文件。如果文件在检查后被删除、权限变化，或文本解码失败，`document_asset_downloads()`、`translation_download()`、`reaction_export_download()` 会抛出异常，导致页面渲染被打断。

## 原因

下载 helper 只处理安全检查阶段的缺失或 symlink 风险，没有处理实际读取阶段的 `OSError` 或 `UnicodeError`。检查和读取之间存在竞态，发布演示或本地操作中可能出现文件刚被清理的情况。

## 修复

在三类下载 helper 的读取阶段捕获 `OSError` 和 `UnicodeError`：文档资产返回 `exists=false` 与缺失提示；翻译下载和反应导出下载返回 `None`，让 Streamlit 页面显示不可下载状态而不是抛异常。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_asset_downloads_report_missing_when_read_fails_after_safety_check tests/test_frontend_api.py::test_translation_download_returns_none_when_read_fails_after_safety_check tests/test_frontend_api.py::test_reaction_export_download_returns_none_when_read_fails_after_safety_check -q` 失败，三个场景都抛出 `FileNotFoundError`。
- GREEN：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_document_asset_downloads_report_missing_when_read_fails_after_safety_check tests/test_frontend_api.py::test_document_asset_downloads_read_pdf_bytes_and_tei_text tests/test_frontend_api.py::test_document_asset_downloads_report_missing_files tests/test_frontend_api.py::test_document_asset_downloads_reject_symlinked_files tests/test_frontend_api.py::test_translation_download_returns_none_when_read_fails_after_safety_check tests/test_frontend_api.py::test_translation_download_reads_markdown_for_streamlit_button tests/test_frontend_api.py::test_translation_download_returns_none_for_missing_output_file tests/test_frontend_api.py::test_translation_download_rejects_symlinked_output_file tests/test_frontend_api.py::test_reaction_export_download_returns_none_when_read_fails_after_safety_check tests/test_frontend_api.py::test_reaction_export_download_reads_text_file_for_streamlit_button tests/test_frontend_api.py::test_reaction_export_download_reads_binary_file_for_non_text_mime tests/test_frontend_api.py::test_reaction_export_download_returns_none_for_missing_output_file tests/test_frontend_api.py::test_reaction_export_download_rejects_symlinked_output_file -q` 通过，`13 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`896 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `896 passed`。
