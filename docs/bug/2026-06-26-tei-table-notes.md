# TEI table notes were dropped

## 现象

- TEI 表格有 `<row>` 数据且同时带 `<note>` 时，`sections_from_tei` 只保留表格行内容。
- `<note>` 中的单位、实验条件、来源说明或“不做单位换算”等原文约束会从 table section 中丢失。
- 这会影响后续化学库抽取和人工复核时回到原文核对。

## 原因

- `append_table` 在存在 table rows 时只使用 `table_rows(table)`。
- `append_figure` 处理 `figure type="table"` 的嵌套 table 时也只拼接 caption 和 rows，没有收集直接子 `<note>`。

## 修复

- 修改文件：`app/services/documents.py`、`tests/test_documents.py`。
- 关键行为：新增 `child_notes`，将 table 或 table figure 的直接 `<note>` 文本追加到 table section 内容中；无 rows 时仍保留原 fallback 行为。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_documents.py::test_sections_from_tei_preserves_table_notes_with_rows -q` 失败，当前内容缺少 table note。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_documents.py tests/test_api.py::test_sections_from_tei_extracts_structured_sections tests/test_api.py::test_sections_from_tei_table_fallback_omits_title_from_content tests/test_api.py::test_sections_from_tei_table_figure_fallback_omits_title_and_duplicate_caption -q` 通过，`8 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`736 passed`。
