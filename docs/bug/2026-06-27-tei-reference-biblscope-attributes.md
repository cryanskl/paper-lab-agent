# TEI reference 页码属性被漏掉

## 现象

GROBID 参考文献中如果使用 `<biblScope unit="page" from="101" to="109"/>` 这类空文本页码范围节点，解析后的 `reference` section 只保留题名、期刊、已有文本卷号和 DOI，页码范围缺失。

## 原因

TEI reference 文本提取只读取元素文本内容。空文本 `biblScope` 的 `from`、`to` 属性没有被转成可检索文本。

## 修复

在 reference 文本提取中识别空文本 `biblScope` 节点的页码范围属性，把 `from/to` 写成原文范围值并加入 reference section，同时继续保留已有文本卷号、日期属性、DOI 和 URL 去重逻辑。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_sections_from_tei_preserves_reference_biblscope_attributes -q` 失败，reference content 缺少 `101-109`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_sections_from_tei_preserves_reference_biblscope_attributes tests/test_api.py::test_sections_from_tei_preserves_reference_date_attributes tests/test_api.py::test_sections_from_tei_extracts_biblstruct_reference_identifiers tests/test_api.py::test_sections_from_tei_extracts_structured_sections -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`883 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `883 passed`。
