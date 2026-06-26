# biblStruct 参考文献丢失 DOI/URL 标识符

## 现象

GROBID TEI 的 `biblStruct` 参考文献可能把 DOI 写在 `idno` 中，把链接写在 `ptr target` 属性中。现有解析只拼接 `itertext()`，会丢失 `ptr target` 里的 URL，也缺少 DOI/URL 的明确标签，影响后续 RAG 引用定位和人工核对。

## 原因

`sections_from_tei()` 处理参考文献时直接使用 `" ".join(bibl.itertext())`。`itertext()` 不包含 XML 属性值，因此 `ptr target`、`ref target` 等标识符不会进入 reference section。

## 修复

为 TEI reference section 增加结构化标识符提取：在正文文本后追加 `idno` 的类型标签和值，并保留 `ptr/ref target` URL；同时避免重复追加已经出现在正文中的值。

## 验证

新增 `test_sections_from_tei_extracts_biblstruct_reference_identifiers` 覆盖 `biblStruct` 中 DOI 与 URL 的解析。完整验证以 `bash scripts/release_check.sh` 为准。

- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
