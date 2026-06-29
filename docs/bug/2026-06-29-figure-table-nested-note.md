# Figure table nested notes were dropped from TEI sections

## 现象

- 触发命令、接口或页面：`sections_from_tei()` 解析 GROBID TEI 中的 `<figure type="table">`，且实际表格内容位于嵌套 `<table>`，表注位于该嵌套 `<table><note>`。
- 实际结果：生成的 `table` section 保留了 figure caption 和表格行，但遗漏嵌套 table note。
- 期望结果：嵌套 table note 应和普通 `<table>` note 一样进入 `table` section content，保留原文出处、单位和人工复核所需说明。

## 原因

- 根因：`append_figure()` 的 `figure type="table"` 分支只读取 `table_rows(nested_table)` 和 `child_notes(figure)`，没有读取 `child_notes(nested_table)`。
- 影响范围：GROBID 输出为 figure-wrapped table 的论文表注、速率/截面来源说明、化学库抽取和后续人工复核证据。

## 修复

- 修改文件：`app/services/documents.py`、`tests/test_documents.py`。
- 关键行为：在嵌套 table 存在时，将 `child_notes(nested_table)` 追加到 table section content；普通 table、figure caption 和 figure 直接 note 行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_documents.py::test_sections_from_tei_preserves_nested_table_notes_inside_table_figures -q` 失败，输出缺少 `Nested table note: values remain in source units.`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_documents.py::test_sections_from_tei_preserves_nested_table_notes_inside_table_figures tests/test_documents.py::test_sections_from_tei_preserves_grobid_table_figure_caption_and_cells tests/test_documents.py::test_sections_from_tei_preserves_table_notes_with_rows tests/test_documents.py::test_sections_from_tei_uses_grobid_labels_for_table_and_figure_titles tests/test_api.py::test_sections_from_tei_extracts_structured_sections tests/test_api.py::test_sections_from_tei_table_figure_fallback_omits_title_and_duplicate_caption -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1260 passed。
