# Reaction export followed symlinked output parents

## 现象

- 触发命令、接口或页面：`export_reaction_set()` 导出已复核 reaction set 的 JSON/TXT/BOLSIG 文件，且 `PAPER_LAB_EXPORT_DIR` 或输出路径父目录链包含 symlink。
- 实际结果：导出流程会跟随 symlink 父目录写入目录外位置，并返回成功导出结果。
- 期望结果：化学库导出路径的父目录链不能包含项目控制外的 symlink；遇到 symlink 父目录时导出失败，不能把复核后的交付物写到配置目录树之外。

## 原因

- 根因：`app/services/chemistry.py` 只在上一阶段检查导出文件本身是否是 symlink，没有检查输出路径父目录链。
- 影响范围：人工复核后的化学库交付物、导出下载文件、本地文件边界。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：导出写入前扫描输出路径父目录链；遇到非系统根级 symlink 父目录时抛出 `reaction export path parent is not a regular directory: ...`，并且不写入 symlink 目标目录。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_reaction_export_rejects_symlinked_output_parent -q` 失败，当前实现没有抛出 `OSError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_reaction_export_rejects_symlinked_output_parent tests/test_api.py::test_reaction_export_rejects_symlinked_output_file tests/test_api.py::test_reaction_export_bolsig_text_and_rejects_unknown_format tests/test_api.py::test_reaction_export_write_failure_returns_json_error -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `801 passed`。
