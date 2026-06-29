# Figure table extra paragraphs were dropped when nested tables existed

## 现象

- 触发命令、接口或页面：`sections_from_tei()` 解析 GROBID TEI 中的 `<figure type="table">`，figure 内同时包含 `<figDesc>`、额外 `<p>` 说明和嵌套 `<table>`。
- 实际结果：生成的 `table` section 保留了 caption 和表格行，但遗漏 figure 里额外段落说明。
- 期望结果：额外段落应进入 `table` section content，用于保留原文单位说明、数据来源说明和人工复核上下文。

## 原因

- 根因：`append_figure()` 的 nested table 分支只读取 caption、table rows、nested table notes 和 figure direct notes；只有没有 nested table 时才走 `content_without_children()` fallback，因此 nested table 存在时 figure 里的额外 `<p>` 被跳过。
- 影响范围：GROBID 输出为 figure-wrapped table 的论文表格说明、RAG 引用摘要、化学库抽取上下文和人工复核证据。

## 修复

- 修改文件：`app/services/documents.py`、`tests/test_documents.py`。
- 关键行为：nested table 分支在读取表格行前，额外保留 figure 中除 head、label、figDesc、nested table 和 direct note 之外的文本；direct note 继续由既有 `child_notes(figure)` 处理，避免重复。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_documents.py::test_sections_from_tei_preserves_table_figure_extra_paragraphs_with_nested_tables -q` 失败，输出缺少 `Only original source units are reported.`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_documents.py::test_sections_from_tei_preserves_table_figure_extra_paragraphs_with_nested_tables tests/test_documents.py::test_sections_from_tei_preserves_nested_table_notes_inside_table_figures tests/test_documents.py::test_sections_from_tei_uses_nested_table_title_inside_table_figures tests/test_documents.py::test_sections_from_tei_uses_grobid_labels_for_table_and_figure_titles tests/test_documents.py::test_sections_from_tei_preserves_grobid_table_figure_caption_and_cells tests/test_api.py::test_sections_from_tei_table_figure_fallback_omits_title_and_duplicate_caption -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1262 passed。
