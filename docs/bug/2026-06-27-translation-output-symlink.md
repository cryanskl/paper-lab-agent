# Translation output followed symlinked markdown path

## 现象

- 触发命令、接口或页面：`translate_document()` 在 translations 目录中生成双语对照 Markdown 文件。
- 实际结果：如果目标输出路径已存在且是 symlink，`Path.write_text()` 会跟随 symlink 写入目录外文件，并把翻译状态标记为 `done`。
- 期望结果：翻译输出路径必须是普通文件或不存在；遇到 symlink 或非普通文件时应失败并记录明确错误，不能覆盖 translations 目录外的文件。

## 原因

- 根因：`app/services/translation.py` 在写入双语 Markdown 前没有检查 `out_path.is_symlink()` 或非普通文件状态。
- 影响范围：文档翻译交付物、本地文件边界、前端下载的翻译 Markdown 可信度。

## 修复

- 修改文件：`app/services/translation.py`、`tests/test_api.py`。
- 关键行为：写入翻译输出前校验目标路径；如果是 symlink 或非普通文件，翻译任务进入 `failed`，`output_path` 置空，`error` 记录 `translation output path is not a regular file: ...`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_translate_document_rejects_symlinked_output_file -q` 失败，当前实现返回 `status='done'` 并写穿 symlink。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_translate_document_rejects_symlinked_output_file tests/test_api.py::test_translate_document_uses_filesystem_safe_target_lang_slug tests/test_api.py::test_translate_document_preserves_table_and_reference_sections tests/test_api.py::test_translate_document_failure_clears_stale_output_path -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `798 passed`。
