# Frontend download helpers followed symlinked files

## 现象

- 触发命令、接口或页面：Streamlit 文档资产下载、翻译结果下载、反应导出下载 helper 接收到指向 symlink 的本地路径。
- 实际结果：helper 跟随 symlink 并读取目标文件内容，把目标内容放入下载 payload。
- 期望结果：symlink 路径不可作为可下载文件，helper 返回缺失状态或 `None`，避免把非预期路径内容暴露给前端下载按钮。

## 原因

- 根因：`document_asset_downloads()`、`translation_download()`、`reaction_export_download()` 只检查 `path.exists()` 与 `path.is_file()`；这两个判定会跟随 symlink，因此不能区分真实文件和 symlinked file。
- 影响范围：Streamlit 本地下载 payload 生成、文档 PDF/TEI 下载、翻译 Markdown 下载、化学反应导出文件下载。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`
- 关键行为：新增共享的 `is_safe_download_file()`，在读取前拒绝路径本身或父级链中任一 symlink；三处下载 helper 均复用该检查，正常真实文件下载行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py -q -k "symlinked_output_file or symlinked_files"` 失败，3 个用例会读取 symlink 目标内容。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py -q -k "download_reads or missing_output_file or missing_files or symlinked_output_file or symlinked_files"` 通过，`9 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `776 passed`。
