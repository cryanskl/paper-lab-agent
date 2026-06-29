# Translation output overwrote colliding target-language slug artifacts

## 现象

- 触发命令、接口或页面：调用 `translate_document()` 为同一 document 生成两次翻译，且 `target_lang` 经过 `safe_target_lang_slug()` 后相同，例如 `zh!` 和 `zh?`。
- 实际结果：两次翻译都写到文件名主体 `document-{id}-zh` 加 `.md` 扩展名的同一路径，后一次可能覆盖前一次。
- 期望结果：第一次保持原文件名；后续 slug 冲突的翻译写入唯一文件名，且不能绕过已有 symlink 或非普通文件安全校验。

## 原因

- 根因：`translate_document()` 直接用 `document_id` 加 target slug 生成固定输出路径，没有考虑历史翻译产物或 slug 冲突。
- 影响范围：文档理解层翻译产物、本地交付物下载、重复翻译或非标准 `target_lang` 的审计可信度。

## 修复

- 修改文件：`app/services/translation.py`、`tests/test_api.py`。
- 关键行为：新增 `translation_output_path()`；基础路径不存在时仍使用文件名主体 `document-{id}-{slug}` 加 `.md` 扩展名，保持既有 `zh` 输出；基础路径为普通文件时追加 `translation_id` 防止覆盖；基础路径不安全时仍返回基础路径并让安全校验失败。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_translate_document_avoids_overwriting_colliding_target_lang_slugs -q` 失败，两次输出均为文件名主体 `document-1-zh` 加 `.md` 扩展名。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_translate_document_avoids_overwriting_colliding_target_lang_slugs tests/test_api.py::test_translate_document_rejects_symlinked_output_file tests/test_api.py::test_translate_document_rejects_symlinked_output_parent tests/test_api.py::test_translate_document_uses_filesystem_safe_target_lang_slug tests/test_api.py::test_translate_document_preserves_table_and_reference_sections -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1259 passed。
