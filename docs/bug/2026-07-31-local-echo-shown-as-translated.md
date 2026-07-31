# Local echo output was shown as translated

## 现象

- 触发页面：“文献库”中点击 `fixture-plasma-chemistry.pdf` 的“打开阅读”。
- 实际结果：左右两栏都是英文，但文献卡片显示“已翻译”，阅读器右栏标为“中文 · 译文”。
- 期望结果：原文回显不能冒充有效译文；应提示用户使用真实翻译引擎重新翻译。

## 原因

- 该文档的历史翻译生成时未配置 `LLM_API_KEY`，`LocalEchoTranslator` 按设计原样保留英文并将任务写成 `done`。
- 前端只根据任务 `status === 'done'` 显示“已翻译”，没有检查目标段落是否真的与原文不同。
- 后来配置真实翻译引擎不会自动重写既有翻译文件，因此旧回显仍会被阅读器读取。

## 修复

- 修改 `web/app.js`：新增有效译文判定，只有至少一个非空目标段落与原文不同，文献卡片才显示“已翻译”。
- 对整篇仅原文回显的记录显示“仅原文 · 请重译”，阅读器中文栏不再重复渲染英文。
- 使用当前已配置的 `qwen-plus` 翻译链路重新翻译本机 fixture，生成新的翻译记录和中文正文；参考文献仍按既有规则保留原文。
- 修改 `tests/test_web_ui.py`：补充原文回显不能被呈现为有效译文的回归约束。

## 验证

- `POST /api/v1/documents/1/translate` 返回新任务，轮询结果为 `status=done`。
- `GET /api/v1/documents/1/translation` 的前四个目标段落为中文，输出路径为 `data/translations/document-1-zh-2.md`。
- 运行聚焦前端测试与浏览器页面验证，确认卡片和双语阅读器显示一致。
- 完整 gate：`EMBEDDING_MODEL=local-hash VECTOR_DB_BACKEND=local-json VECTOR_DB_PATH=data/vector-index.json bash scripts/release_check.sh` → `1375 passed in 188.74s`。
