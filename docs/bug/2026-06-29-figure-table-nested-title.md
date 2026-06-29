# Figure table nested titles were replaced by generated titles

## 现象

- 触发命令、接口或页面：`sections_from_tei()` 解析 GROBID TEI 中的 `<figure type="table">`，figure 自身没有 `<head>` 或 `<label>`，但内部 `<table>` 带有 `<head>` 或 `<label>`。
- 实际结果：生成的 `table` section 标题退回为 `Table 1` 这类顺序标题，丢失源论文中的真实表号或表题。
- 期望结果：figure 自身没有标题时，应使用嵌套 table 的 head 或 label 作为 `table` section title，便于章节浏览、引用定位和化学库复核追溯。

## 原因

- 根因：`append_figure()` 的 `figure type="table"` 分支始终用 figure 节点调用 `title_from_head_or_label()`，没有把 nested table 作为标题回退来源。
- 影响范围：GROBID 输出为 figure-wrapped table 的论文表号、表题、RAG 引用定位和人工复核证据定位。

## 修复

- 修改文件：`app/services/documents.py`、`tests/test_documents.py`。
- 关键行为：保留 figure 自身 head/label 的优先级；当 figure 没有标题且存在 nested table 时，使用 nested table 的 head/label；两者都没有时才继续生成顺序标题。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_documents.py::test_sections_from_tei_uses_nested_table_title_inside_table_figures -q` 失败，标题实际为 `Table 1` 而不是 `Table 5`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_documents.py::test_sections_from_tei_uses_nested_table_title_inside_table_figures tests/test_documents.py::test_sections_from_tei_preserves_nested_table_notes_inside_table_figures tests/test_documents.py::test_sections_from_tei_uses_grobid_labels_for_table_and_figure_titles tests/test_documents.py::test_sections_from_tei_preserves_grobid_table_figure_caption_and_cells tests/test_api.py::test_sections_from_tei_table_figure_fallback_omits_title_and_duplicate_caption tests/test_api.py::test_sections_from_tei_extracts_structured_sections -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1261 passed。
