# Translation could silently drop formula placeholders

## 现象

翻译链路会先把公式替换为 `<EQ_000>` 这类占位符，再交给 translator。若外部 LLM 没有按要求原样保留占位符，当前实现会继续生成译文，导致公式无法回填，最终译文丢失原文公式。

## 原因

`translate_text_preserving_formulas` 只在 translator 返回后做字符串替换，没有校验所有公式占位符是否仍存在。占位符缺失时，`unmask_formulas` 没有可替换目标，也不会报错。

## 修复

新增 `validate_formula_placeholders`，在公式回填前检查 translator 响应必须包含全部 `<EQ_...>` 占位符。缺失时抛出 `ValueError: translation response missing formula placeholder <EQ_000>`，让翻译任务进入 failed 状态并记录明确原因。

## 验证

新增占位符丢失异常路径测试，并确认原有公式保护、文档翻译失败清理和表格/参考文献保留测试仍通过：

```bash
python -m pytest tests/test_api.py::test_translation_adapter_preserves_formula_masks tests/test_api.py::test_translation_adapter_reports_missing_formula_placeholder tests/test_api.py::test_translate_document_failure_clears_stale_output_path tests/test_api.py::test_translate_document_preserves_table_and_reference_sections -q
```
