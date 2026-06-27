# Reaction export followed symlinked output files

## 现象

- 触发命令、接口或页面：`export_reaction_set()` 导出已复核 reaction set 的 JSON/TXT/BOLSIG 文件。
- 实际结果：如果目标导出文件已存在且是 symlink，`Path.write_text()` 会跟随 symlink 写入目录外文件，并返回成功导出结果。
- 期望结果：化学库导出目标路径必须是普通文件或不存在；遇到 symlink 或非普通文件时导出失败，不能覆盖 `PAPER_LAB_EXPORT_DIR` 外的文件。

## 原因

- 根因：`app/services/chemistry.py` 在写入 reaction export 文件前没有检查 `out_path.is_symlink()` 或非普通文件状态。
- 影响范围：人工复核后的化学库交付物、导出下载文件、本地文件边界。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：JSON/TXT/BOLSIG 三种导出格式共用写入前路径校验；如果目标路径是 symlink 或非普通文件，抛出 `reaction export path is not a regular file: ...`，API 层按既有规则返回 `reaction_export_failed`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_reaction_export_rejects_symlinked_output_file -q` 失败，当前实现没有抛出 `OSError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_reaction_export_rejects_symlinked_output_file tests/test_api.py::test_reaction_export_bolsig_text_and_rejects_unknown_format tests/test_api.py::test_reaction_export_rejects_empty_reaction_set tests/test_api.py::test_reaction_export_write_failure_returns_json_error -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `800 passed`。
