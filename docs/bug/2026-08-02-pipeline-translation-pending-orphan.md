# 文档流水线异常会遗留 pending 翻译任务

## 现象

自动处理流水线先创建 `translations.status='pending'` 记录，再在线程池执行 `translate_document()`。如果执行器在翻译函数正常失败处理之外抛出异常，流水线响应会把 translation 标为 failed，但数据库记录仍永久停在 pending；前端会持续显示“翻译中”并轮询。

## 原因

`translate_document()` 内部的常规异常会更新 failed，但 `run_document_pipeline()` 的外层异常分支只组装内存结果，没有终结已经创建的 translation job。API/数据库两个状态来源因此分叉。

## 修复

- 提取 `mark_translation_failed()`，统一写入 `status=failed`、清空 `output_path` 并保留错误信息。
- `translate_document()` 的常规失败和流水线外层兜底共同调用该函数。
- 如果失败终结本身也异常，流水线合并两层错误但继续运行 index 与 chemistry，保持派生阶段互不阻塞。

## 验证

- RED：真实创建 pending translation，再让流水线的翻译 worker 抛出 `translation worker crashed`；旧响应为 failed，但数据库仍为 pending。
- GREEN：数据库记录变为 failed、`output_path` 为 null、错误信息准确；同一流水线的 index 和 chemistry 继续完成。上传/流水线/翻译聚焦组 `26 passed`。
- 完整 gate：`bash scripts/release_check.sh` 的 preflight、demo、health、package、smoke 全部通过；全量测试 `1424 passed, 5 warnings in 241.63s`。
