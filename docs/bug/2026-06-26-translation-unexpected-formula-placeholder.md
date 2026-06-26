# Translation could leave unexpected formula placeholders

## 现象

翻译链路要求 translator 原样保留由系统生成的 `<EQ_...>` 公式占位符。若外部 LLM 额外生成一个不存在的占位符，例如 `<EQ_999>`，当前实现会在回填已知公式后把这个伪造占位符残留在最终译文中。

## 原因

`validate_formula_placeholders` 只检查原有占位符是否缺失，没有检查 translator 响应中是否出现了不属于本次公式掩码集合的额外 `<EQ_...>`。

## 修复

新增 `FORMULA_PLACEHOLDER_RE`，在回填前扫描 translator 响应中的所有公式占位符。任何不属于本次 `formulas` 映射的占位符都会触发 `ValueError: translation response unexpected formula placeholder <EQ_999>`。

## 验证

新增额外公式占位符异常路径测试，并确认原有公式保护、占位符缺失、文档翻译失败清理和表格/参考文献保留测试仍通过：

```bash
python -m pytest tests/test_api.py::test_translation_adapter_preserves_formula_masks tests/test_api.py::test_translation_adapter_reports_missing_formula_placeholder tests/test_api.py::test_translation_adapter_reports_unexpected_formula_placeholder tests/test_api.py::test_translate_document_failure_clears_stale_output_path tests/test_api.py::test_translate_document_preserves_table_and_reference_sections -q
```

- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
