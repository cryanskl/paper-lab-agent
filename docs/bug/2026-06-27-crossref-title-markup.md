# Crossref 标题和期刊名保留 JATS 标记

- 日期：2026-06-27
- 触发命令、接口或页面：OpenAlex 无结果或失败后使用 Crossref fallback 抓取元数据，Crossref `title` 或 `container-title` 含 JATS/HTML 标记。
- 影响范围：确定性抓取层的 Crossref 归一化、关键词过滤、论文标题展示和期刊名展示。

## 现象

Crossref 的摘要已经会清理 JATS/HTML 标记，但标题和期刊名仍直接使用 `first_text()` 返回原始字符串。例如 `Ar/O<jats:sub>2</jats:sub> <jats:italic>plasma</jats:italic>` 会原样进入 `papers.title`，既影响前端展示，也可能让关键词短语匹配被标签打断。

## 原因

`CrossrefClient.clean_abstract()` 只用于 `abstract` 字段，`title`、`subtitle` 和 `container-title` 通过 `first_text()` 直接取值，没有统一文本清理步骤。

## 修复

- 新增 Crossref 通用 `clean_text()`，先对段落/表格等块级标签补空格，再移除其余内联标签并 HTML unescape。
- `clean_abstract()` 复用同一清理逻辑。
- `first_text()` 对字符串、列表项和默认文本统一清理，确保标题、subtitle fallback 和期刊名都是纯文本。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_crossref_client_strips_jats_tags_from_title_and_journal_name -q` 失败，标题仍包含 `<jats:sub>`、`<jats:italic>` 和 `&amp;`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_crossref_client_strips_jats_tags_from_title_and_journal_name tests/test_api.py::test_crossref_client_strips_jats_tags_from_abstract tests/test_api.py::test_crossref_client_uses_issued_date_when_published_dates_are_missing tests/test_api.py::test_crossref_client_paginates -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`870 passed`；`bash scripts/release_check.sh` 通过。
