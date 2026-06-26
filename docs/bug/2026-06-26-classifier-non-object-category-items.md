# Classifier category item type errors were opaque

## 现象

OpenAI-compatible 分类 adapter 收到 `categories` 数组但其中元素不是对象时，例如 `{"categories":["chemistry"]}`，会在归一化阶段抛出 `AttributeError: 'str' object has no attribute 'get'`。这个错误无法直接说明是 LLM 分类响应格式不符合契约。

## 原因

`parse_classifier_response_content` 只校验了 `categories` 是数组，`normalize_classifier_results` 随后默认每个数组元素都是对象并调用 `item.get(...)`。

## 修复

`parse_classifier_response_content` 现在要求 `categories` 中每个元素都是 JSON object。非对象元素会统一抛出 `ValueError: classifier response categories items must be JSON objects`。

## 验证

新增非对象 category item 异常路径测试，并确认分类成功路径和既有异常路径仍通过：

```bash
python -m pytest tests/test_api.py::test_openai_classifier_keeps_only_registered_taxonomy_slugs tests/test_api.py::test_openai_classifier_reports_invalid_chat_completion_shape tests/test_api.py::test_openai_classifier_reports_invalid_json_content tests/test_api.py::test_openai_classifier_reports_non_object_json_content tests/test_api.py::test_openai_classifier_reports_missing_categories_field tests/test_api.py::test_openai_classifier_reports_non_list_categories_field tests/test_api.py::test_openai_classifier_reports_non_object_category_items tests/test_api.py::test_classify_paper_failure_returns_json_error -q
```
