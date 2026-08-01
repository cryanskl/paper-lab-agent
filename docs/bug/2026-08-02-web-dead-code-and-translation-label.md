# Web 前端遗留死代码与翻译状态旧文案

## 现象

Web bundle 中保留了从未调用的 `el()` 元素工厂，并同时存在语义完全相同的 `wait()` 与 `delay()`。此外，系统状态 API 在未配置模型时已经返回 `translation_adapter=unavailable`，侧栏仍显示“本地回显”，与翻译端点的 409 语义冲突。

## 原因

前端多轮演进后，旧 DOM helper 没有随调用点删除，术语翻译又新增了一份独立延时 helper。离线翻译从 local echo 改为 unavailable 时，发布、API 和主要工作台状态已同步，但侧栏消费者文案遗漏。

## 修复

- 删除调用计数为零的 `el()`。
- 术语翻译轮询复用已有 `delay()`，删除重复 `wait()`。
- 翻译 adapter 不是 `openai-compatible` 时，侧栏显示“不可用”，不再暗示存在本地回显翻译能力。
- 保留 `LocalEchoTranslator` 诊断类及其防误用检查，因为它仍承担显式回归测试和降级保护职责。

## 验证

- RED：前端契约检查确认旧 bundle 仍包含 `el()`、`wait()` 和“本地回显”。
- GREEN：`node --check web/app.js` 通过；两个聚焦用例通过；`tests/test_web_ui.py` 全量 `67 passed`。
- 清理复核：对所有具名 Web 函数重新统计声明和标识符引用，未发现只出现于声明处的零引用函数。
- 完整 gate：`bash scripts/release_check.sh` 的 preflight、demo、health、package、smoke 全部通过；全量测试 `1425 passed, 5 warnings in 239.82s`。
