# Classifier invalid JSON content errors were opaque

## 现象

OpenAI-compatible 分类 adapter 收到合法 chat completion 外壳、但 `message.content` 不是分类 JSON 时，会暴露底层异常。例如内容为 `not json` 时抛出 `JSONDecodeError`，内容为 `[]` 时在后续 `.get()` 调用中抛出 `AttributeError`。

## 原因

分类 adapter 只校验了 chat completion 外层结构，随后直接 `json.loads` 并假设结果一定是对象。上游模型输出自由文本、数组或其他非对象 JSON 时，错误信息无法稳定指向分类响应内容格式问题。

## 修复

新增 `parse_classifier_response_content`，先剥离 JSON fence，再校验内容必须是合法 JSON 对象。非法 JSON 统一抛出 `ValueError: classifier response content is not valid JSON`；非对象 JSON 统一抛出 `ValueError: classifier response content must be a JSON object`。

## 验证

新增分类 adapter 的非法 JSON 和非对象 JSON 测试，并确认原有成功路径和分类失败 JSON 响应测试仍通过：

```bash
python -m pytest tests/test_api.py::test_openai_classifier_keeps_only_registered_taxonomy_slugs tests/test_api.py::test_openai_classifier_reports_invalid_chat_completion_shape tests/test_api.py::test_openai_classifier_reports_invalid_json_content tests/test_api.py::test_openai_classifier_reports_non_object_json_content tests/test_api.py::test_classify_paper_failure_returns_json_error -q
```

- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
