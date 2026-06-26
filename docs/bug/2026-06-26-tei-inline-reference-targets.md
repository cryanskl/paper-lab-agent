# TEI 正文内联引用丢失 target URL

## 现象

GROBID TEI 的正文、列表、表格单元格和图注可能使用 `ref target` 或 `ptr target` 标注数据来源链接。现有解析只保留可见文本，丢失 target URL，导致 RAG 来源片段和化学库人工复核时无法看到原始数据链接。

## 原因

`sections_from_tei()` 在多个正文抽取路径中直接使用 `itertext()`。`itertext()` 不包含 XML 属性值，因此 `ref target`、`ptr target` 这类来源 URL 不会进入 section content。

## 修复

新增混合文本抽取辅助函数，递归保留文本、子节点 tail 和 `ref/ptr target`。普通章节会把内联引用写成 `显示文本 (URL)`，无显示文本的 `ptr` 直接写入 URL；标题和参考文献主体继续避免混入 target，参考文献 URL 仍由专门逻辑追加。

## 验证

新增 `test_sections_from_tei_preserves_inline_reference_targets` 覆盖正文段落、列表项、表格单元格和图注中的内联 target。完整验证以 `bash scripts/release_check.sh` 为准。

- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
