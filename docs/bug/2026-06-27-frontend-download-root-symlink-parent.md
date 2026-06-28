# Frontend downloads rejected files under system root symlink parents

## 现象

- 触发命令、接口或页面：Streamlit 前端下载 PDF、TEI、翻译或反应导出文件，文件路径位于 macOS `/var/tmp`、`/var/folders` 等系统根级 symlink 路径下。
- 实际结果：`is_safe_download_file()` 扫描所有父目录 symlink，命中 `/var -> /private/var` 后把普通文件误判为不安全，下载 helper 返回缺失状态。
- 期望结果：下载 helper 应允许系统根级 symlink 父目录下的普通文件，同时继续拒绝文件本身 symlink 和普通中间目录 symlink。

## 原因

- 根因：`app/frontend_api.py` 的 `is_safe_download_file()` 使用 `any(candidate.is_symlink() for candidate in (path, *path.parents))`，没有区分系统根级 symlink 与用户可控中间目录 symlink。
- 影响范围：本机 demo、release smoke 或临时目录下生成的可下载 PDF/TEI/翻译/导出文件，在 macOS 上可能无法从 Streamlit 下载。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：下载安全检查允许 `candidate.parent == Path(candidate.anchor)` 的系统根级 symlink；其他 symlink 仍拒绝。正常真实文件下载恢复，已有 symlink 文件拒绝策略保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_frontend_download_allows_system_root_symlink_parent -q` 失败，当前实现返回 `False`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_frontend_download_allows_system_root_symlink_parent tests/test_frontend_api.py::test_document_asset_downloads_reject_symlinked_files tests/test_frontend_api.py::test_translation_download_rejects_symlinked_output_file tests/test_frontend_api.py::test_reaction_export_download_rejects_symlinked_output_file -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `811 passed`。
