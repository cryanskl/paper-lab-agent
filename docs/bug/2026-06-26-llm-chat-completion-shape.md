# LLM chat completion shape errors were opaque

## 现象

OpenAI-compatible 翻译或分类 adapter 收到异常 chat completion 响应时，例如 `{"choices":[]}` 或缺少 `message.content`，会抛出裸的 `IndexError` / `KeyError`。这些异常会进入翻译或分类任务错误字段，难以判断是上游 LLM 响应结构问题。

## 原因

翻译和分类 adapter 直接索引 `response.json()["choices"][0]["message"]["content"]`，没有先校验响应 shape 和 content 类型。

## 修复

新增共享的 `chat_completion_content` helper，统一校验 `choices[0].message.content` 是否存在且为非空字符串。无效响应现在抛出清晰的 `ValueError: chat completion response missing choices[0].message.content`。

## 验证

新增翻译和分类 adapter 的异常 shape 测试，并确认原有成功路径仍通过：

```bash
python -m pytest tests/test_api.py::test_openai_translation_adapter_uses_compatible_chat_completions_payload tests/test_api.py::test_openai_translation_adapter_reports_invalid_chat_completion_shape tests/test_api.py::test_openai_classifier_keeps_only_registered_taxonomy_slugs tests/test_api.py::test_openai_classifier_reports_invalid_chat_completion_shape -q
```
