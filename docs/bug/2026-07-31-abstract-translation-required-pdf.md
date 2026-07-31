# 摘要翻译错误依赖 PDF 全文

- 日期：2026-07-31
- 触发页面：文献检索结果卡片 → `摘要翻译`
- 影响范围：仅有检索元数据摘要、尚未上传 PDF 的论文

## 现象

论文卡片已经显示英文摘要，但点击 `摘要翻译` 后提示必须先上传 PDF 并执行全文解析与翻译，无法直接翻译现有摘要。

## 原因

前端 `showAbstractTranslation()` 没有使用论文记录的 `abstract`，而是先按
`paper_id` 查找已导入的 `documents`，再从全文翻译结果中挑选
`section_type=abstract` 的段落。元数据摘要与 PDF 全文被错误绑定为同一资源生命周期。

## 修复

- 新增独立的论文摘要翻译异步接口与 `paper_abstract_translations` 缓存表。
- 摘要翻译直接读取 `papers.abstract`，不依赖 `documents`、GROBID 或 PDF 全文翻译。
- 缓存键包含论文、目标语言和摘要快照；摘要更新后不会复用旧译文。
- 前端展示翻译中、完成和失败状态；没有摘要时才显示缺失提示。

## 验证

- API 回归覆盖：无 document 的论文可翻译摘要、相同摘要复用缓存、缺失摘要返回
  `409 paper_abstract_missing`。
- Web UI 静态回归确认按钮调用 `/papers/{id}/abstract-translation`，旧 PDF 提示已移除。
- schema、API contract 与 Python 编译校验通过。
- 完整 gate：`EMBEDDING_MODEL=local-hash VECTOR_DB_BACKEND=local-json VECTOR_DB_PATH=data/vector-index.json bash scripts/release_check.sh` → `1375 passed in 188.74s`。
