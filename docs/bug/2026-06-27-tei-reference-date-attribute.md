# TEI reference 日期属性被漏掉

## 现象

GROBID 参考文献中如果使用 `<date when="2026"/>` 这类空文本日期节点，解析后的 `reference` section 只保留题名、期刊和 DOI，年份缺失。

## 原因

TEI reference 文本提取只读取元素文本内容。空文本 `<date>` 的 `when`、`from`、`to` 等属性没有被转成可检索文本。

## 修复

在 reference 文本提取中识别空文本日期节点的日期属性，把属性值写入 reference section，同时保持已有文本日期和 DOI/URL 去重逻辑。

## 验证

新增回归：`.venv/bin/python -m pytest tests/test_api.py::test_sections_from_tei_preserves_reference_date_attributes -q`，结果 `1 passed`。

局部回归：`.venv/bin/python -m pytest tests/test_api.py::test_sections_from_tei_preserves_reference_date_attributes tests/test_api.py::test_sections_from_tei_extracts_biblstruct_reference_identifiers tests/test_api.py::test_sections_from_tei_extracts_structured_sections tests/test_api.py::test_sections_from_tei_preserves_inline_reference_targets -q`，结果 `4 passed`。

- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`882 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `882 passed`。
