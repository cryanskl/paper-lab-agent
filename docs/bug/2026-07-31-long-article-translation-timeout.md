# 长文章翻译读取超时

## 现象

较长 PDF 完成解析后触发翻译，任务变为 `failed`，错误为
`The read operation timed out`。前端因此显示“翻译失败”。

## 原因

翻译流水线按 `sections` 逐节调用模型，但没有限制单节文本大小。GROBID
可能把多页正文合并为一个长章节，使一次 `/chat/completions` 请求承担整段正文；
客户端同时使用固定 60 秒超时，长输出尚未返回便被中止。

## 修复

- 公式先整体替换为占位符，避免分块切断公式。
- 超长章节优先按段落、换行和句末边界切成不超过
  `TRANSLATION_CHUNK_CHARS` 的请求，默认 6000 字符。
- 所有分块完成后统一校验公式占位符并回填。
- 模型请求超时改由 `LLM_REQUEST_TIMEOUT_SECONDS` 配置，默认 180 秒。

## 验证

- 单次提交给 translator 的文本不得超过配置上限。
- 长文本跨分块后的公式必须原样保留。
- 短文本仍只调用模型一次。
- 任一分块失败时，现有任务状态仍写为 `failed` 并保留错误原因。
- 聚焦翻译回归：`.venv/bin/python -m pytest -q tests/test_api.py -k
  'translation_adapter or translate_document or paper_abstract_translation'`
  → `18 passed`。
- 配置与翻译契约回归：`.venv/bin/python -m pytest -q
  tests/test_release_contracts.py -k 'env_example or translation_response or
  translation_adapter'` → `41 passed`。
- 完整 gate：`EMBEDDING_MODEL=local-hash VECTOR_DB_BACKEND=local-json VECTOR_DB_PATH=./data/vector-index.json bash scripts/release_check.sh` 完成 `1392 passed, 1 failed`；唯一失败是并行工作区中
  `tests/test_web_ui.py` 期待 `projectsForDocument`、而 `web/app.js` 仍为
  `projectForDocument` 的既有多项目归属改动，不涉及本次翻译链路。
- 真实长文验证：重新触发 21 页 `document_id=20`，36,718 个待译字符按
  6,000 字符上限形成 23 次模型请求；任务 `id=5` 最终为 `done`、
  `error=null`，在运行时翻译目录生成 document-20-zh.md，并返回 73 个
  双语章节。工作台卡片由“翻译失败”更新为“已翻译”，旧超时信息消失，
  浏览器控制台无 warning/error。
