# TEI 正文公式节点被漏掉

## 现象

GROBID TEI 正文中如果把公式写成独立 `<formula>` 或 `<equation>` 节点，解析后的 `body` section 只保留前后段落，公式文本缺失。后续翻译、RAG、化学抽取都无法看到该公式证据。

## 原因

TEI body/div 遍历只把 `p` 和 `list` 当作正文内容节点处理。`formula`、`equation` 没有进入 `content_parts`，因此被直接跳过。

## 修复

在 body 和 div 的正文解析中把 `formula`、`equation` 作为正文片段处理，使用同一 `text_content()` 逻辑保留公式文本，并保持 table/figure 的分段行为不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_sections_from_tei_body_includes_direct_formula_nodes -q` 失败，body content 缺少 `k_i = n_e n_Ar <sigma v>`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_sections_from_tei_body_includes_direct_formula_nodes tests/test_api.py::test_sections_from_tei_body_includes_direct_list_items tests/test_api.py::test_sections_from_tei_preserves_div_table_document_order tests/test_api.py::test_sections_from_tei_extracts_direct_body_paragraphs -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`884 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `884 passed`。
