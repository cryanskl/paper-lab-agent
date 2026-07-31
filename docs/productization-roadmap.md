# paper-lab-agent 成品化路线

本文档承接 `docs/PRD_等离子体文献系统.md`，用于把当前可运行 skeleton 推进到可长期使用的本地产品。开发仍以 `docs/接口设计文档.md` 和 `docs/schema.sql` 为真理来源。

## P0 · 可持续运行基础

目标：让系统不依赖手工造数据也能稳定演示、测试和排障。

- 配置校验：启动时能报告外部能力是否已配置，但不阻断本地离线模式。
- 调度器：APScheduler 注册 daily / weekly / monthly crawl 入口，调用同一 crawl 编排逻辑。
- Fixture 导入：提供离线导入论文和文档样例的 CLI，支撑 walking skeleton。
- Job 状态一致性：后台任务失败时写入资源状态和错误说明。
- 测试：覆盖 seed 数据、fixture 导入、crawl job 创建、papers 检索、文档理解链路。

## P1 · 确定性检索层成品化

目标：白名单检索层可真实连接 OpenAlex / Crossref / Unpaywall，并且失败可诊断。

- OpenAlex / Crossref 分页、重试、限流和字段归一化增强。
- 用户搜索词支持 AND / OR 语义，并下推到 OpenAlex / Crossref；期刊配置不再承担关键词准入。
- 精确重复搜索复用本地缓存，并以可配置的结果数量控制响应时间。
- 多期刊搜索先收集全部候选，再按期刊内相关性和跨期刊轮转填充全局配额，避免快源垄断结果。
- crawl job 详情展示每个期刊的 found/new/filtered/error。
- DOI 为空的文献建立保守去重策略和审计字段。
- Streamlit 检索页增加手动抓取、job 列表和 job 详情。

## P2 · 文档理解层成品化

目标：PDF 导入、GROBID 解析、翻译、RAG 都能服务真实论文。

- GROBID 健康检查和失败原因进入 API。
- TEI 解析覆盖 abstract、body、table、figure caption、reference。
- 翻译使用可插拔 LLM adapter，同时保留本地诊断回显和公式掩码测试；回显不得展示为有效译文。
- RAG 同时保留 `local-hash` / `local-json` 离线基线，并支持 `bge-m3` / Chroma 跨语言检索；切换模型后必须重建索引。
- Streamlit 文档页支持章节浏览、翻译预览、索引状态和引用定位。

## P3 · 化学库交付成品化

目标：反应集抽取、复核、导出成为可审计交付物。

- 抽取结果保留来源 section、表号/出处、confidence 和失败原因。
- 支持人工编辑 reaction_type、rate_type、rate_value、threshold_ev、cross_section_url。
- 导出 JSON 与 BOLSIG+/LXCat 兼容文本。
- 复核记录进入审计日志，至少记录 verified_by、verified_at 和修正后值。
- Streamlit 复核页支持逐条编辑、批量查看未复核项和导出。

## P4 · 打包与运行体验

目标：新机器可按文档完整启动。

- README 覆盖后端、前端、测试、fixture 导入、GROBID 可选启动方式。
- 提供 `scripts/dev.sh` 或等价命令，统一启动 API 与 Streamlit。
- 提供健康检查命令和常见问题排查。
- CI 可跑默认离线测试。
