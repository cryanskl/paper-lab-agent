# Translation missed wide formula placeholders

## 现象

公式掩码使用 `<EQ_000>` 这类占位符。当前校验能阻止额外的三位占位符，例如 `<EQ_999>`，但无法识别更多位数字的占位符，例如 `<EQ_1000>`。如果外部 LLM 额外生成这种占位符，它会残留在最终译文中。

## 原因

`FORMULA_PLACEHOLDER_RE` 只匹配 `<EQ_\d{3}>`。当占位符数字超过三位，或模型伪造更多位数字的占位符时，额外占位符扫描不会命中。

## 修复

将公式占位符检测正则改为 `<EQ_\d+>`，让缺失/额外占位符校验覆盖任意位数字，与 `mask_formulas` 的实际编号行为一致。

## 验证

新增 `<EQ_1000>` 额外占位符异常路径测试，并确认原有公式保护、占位符缺失和三位额外占位符测试仍通过：

```bash
python -m pytest tests/test_api.py::test_translation_adapter_preserves_formula_masks tests/test_api.py::test_translation_adapter_reports_missing_formula_placeholder tests/test_api.py::test_translation_adapter_reports_unexpected_formula_placeholder tests/test_api.py::test_translation_adapter_reports_unexpected_wide_formula_placeholder tests/test_api.py::test_translate_document_failure_clears_stale_output_path tests/test_api.py::test_translate_document_preserves_table_and_reference_sections -q
```

- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
