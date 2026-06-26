# Classifier accepted malformed categories payloads

## 现象

OpenAI-compatible 分类 adapter 收到合法 JSON 对象但缺少 `categories` 字段，或 `categories` 不是数组时，会静默返回空分类结果。这会让上游模型输出格式错误看起来像“模型判断没有任何分类”，影响分类任务排障。

## 原因

分类 adapter 使用 `data.get("categories") or []`，并在非列表时继续降级为空列表。这个 fallback 掩盖了与 prompt 约定不一致的 LLM 响应。

## 修复

`parse_classifier_response_content` 现在要求响应内容必须包含 `categories` 数组。缺失或类型错误时统一抛出 `ValueError: classifier response content missing categories list`，只有合法数组才进入分类 slug 归一化。

## 验证

新增 `categories` 缺失和非数组两类异常路径测试，并确认分类成功路径与既有异常路径仍通过：

```bash
python -m pytest tests/test_api.py::test_openai_classifier_keeps_only_registered_taxonomy_slugs tests/test_api.py::test_openai_classifier_reports_invalid_chat_completion_shape tests/test_api.py::test_openai_classifier_reports_invalid_json_content tests/test_api.py::test_openai_classifier_reports_non_object_json_content tests/test_api.py::test_openai_classifier_reports_missing_categories_field tests/test_api.py::test_openai_classifier_reports_non_list_categories_field tests/test_api.py::test_classify_paper_failure_returns_json_error -q
```

- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
