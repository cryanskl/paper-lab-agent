# Translation output followed symlinked output parents

## 现象

- 触发命令、接口或页面：`translate_document()` 在 translations 目录中生成双语对照 Markdown 文件，且 `PAPER_LAB_TRANSLATION_DIR` 或输出路径父目录链包含 symlink。
- 实际结果：翻译流程会跟随 symlink 父目录写入目录外位置，并把翻译状态标记为 `done`。
- 期望结果：翻译输出路径的父目录链不能包含项目控制外的 symlink；遇到 symlink 父目录时翻译任务应失败，不能把双语 Markdown 写到配置目录树之外。

## 原因

- 根因：`app/services/translation.py` 只检查翻译输出文件本身是否是 symlink 或非普通文件，没有检查输出路径父目录链。
- 影响范围：文档翻译交付物、本地文件边界、前端下载的翻译 Markdown 可信度。

## 修复

- 修改文件：`app/services/translation.py`、`tests/test_api.py`。
- 关键行为：写入翻译输出前扫描输出路径父目录链；遇到非系统根级 symlink 父目录时任务进入 `failed`，`output_path` 置空，`error` 记录 `translation output path parent is not a regular directory: ...`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_translate_document_rejects_symlinked_output_parent -q` 失败，当前实现返回 `status='done'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_translate_document_rejects_symlinked_output_parent tests/test_api.py::test_translate_document_rejects_symlinked_output_file tests/test_api.py::test_translate_document_uses_filesystem_safe_target_lang_slug tests/test_api.py::test_translate_document_failure_clears_stale_output_path -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `802 passed`。
