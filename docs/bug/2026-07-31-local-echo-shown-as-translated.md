# Local echo output was shown as translated

## 现象

- 触发页面：“文献库”中点击 `fixture-plasma-chemistry.pdf` 的“打开阅读”。
- 实际结果：左右两栏都是英文，但文献卡片显示“已翻译”，阅读器右栏标为“中文 · 译文”。
- 期望结果：原文回显不能冒充有效译文；应提示用户使用真实翻译引擎重新翻译。

## 原因

- 该文档的历史翻译生成时未配置 `LLM_API_KEY`，`LocalEchoTranslator` 按设计原样保留英文并将任务写成 `done`。
- 前端最初只根据任务 `status === 'done'` 显示“已翻译”，没有检查目标段落是否真的与原文不同。
- 后来配置真实翻译引擎不会自动重写既有翻译文件，因此旧回显仍会被阅读器读取。
- 2026-08-02 的代码审查进一步确认：演示数据和 release smoke 也会强制使用 echo adapter，并把这条假成功记录计入发布就绪状态；问题不只在展示层。

## 修复

- 展示层保留有效译文判定：只有至少一个非空目标段落与原文不同，文献卡片才显示“已翻译”；历史 echo 记录显示“仅原文 · 请重译”。
- 服务层不再把 `LocalEchoTranslator` 当成生产翻译能力；文档、摘要和术语翻译在缺少 `LLM_API_KEY` 时返回 `409 translation_unavailable`，并且不创建翻译任务。
- 自动文档流水线把翻译记为可选的 `unavailable` 阶段，同时继续索引和化学抽取。
- 演示数据、系统状态、health check、release smoke 和发布产物统一使用 `translation_status=unavailable`、`translation_adapter=unavailable`，并断言离线演示的翻译记录数为 0。
- 补充服务、API、流水线与发布契约回归测试，覆盖 echo 不得写成 `done`、无 key 不得创建任务以及其它文档阶段继续执行。

## 验证

- 聚焦 API 回归：`.venv/bin/python -m pytest tests/test_abstract_translation.py tests/test_api.py -q --tb=short` → `660 passed`。
- 发布契约回归：`.venv/bin/python -m pytest tests/test_release_contracts.py -q --tb=short` → `388 passed`。
- 完整 gate：`bash scripts/release_check.sh` → preflight、demo、health、package、smoke 全部通过；smoke 返回 `translation_unavailable`、`translations={}`、`release_ready=true`；全量测试 `1418 passed, 5 warnings in 263.74s`。
