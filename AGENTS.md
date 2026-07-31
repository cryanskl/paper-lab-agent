# AGENTS.md

> 给 AI 编码 agent（Claude Code / Cursor 等）的项目上下文。每次开始任务前先读本文件。
> Cursor 用户可把本文件内容放进 `.cursorrules`。

## 项目一句话

低温等离子体文献检索与理解系统：确定性检索层（按白名单 ISSN 限定期刊、按用户 OR/AND 搜索词联网检索并本地缓存）+ 大模型理解层（翻译 / RAG / 化学库抽取）。详见 `docs/PRD_等离子体文献系统.md`。

## 真理来源（不得擅自改动）

- **数据模型** = `docs/schema.sql`。不得自行新增表、改字段名或类型。确需变更：先改 `docs/schema.sql` 并说明，再写代码。
- **接口契约** = `docs/接口设计文档.md`。端点路径、方法、请求/响应结构以它为准，不得自创端点或改路径。
- **范围与优先级** = PRD。不做 PRD 第 2 节"非目标"里的事。
- **任务与顺序** = `docs/任务拆分_开发路线.md`。一次只做一个任务，满足其验收标准才算完成。

## 技术栈（锁定）

FastAPI + SQLite + APScheduler + GROBID + Chroma/FAISS；前端 Streamlit。未经讨论不要替换或引入重型框架。

## 通用约定

- 响应一律 JSON；列表统一 `{items,total,page,page_size}`；错误统一 `{error:{code,message}}` + 语义化 HTTP 状态码。
- 耗时操作（抓取/解析/翻译/索引/抽取）用 FastAPI BackgroundTasks 异步，立即返回后由资源的 status 字段轮询；不要做成同步阻塞。
- 日期统一 ISO8601 文本；多值字段（authors/keywords/reactants 等）统一存 JSON 文本。
- SQLite 连接开启 `PRAGMA foreign_keys=ON`；检索走已建好的 `papers_fts`（FTS5），不要自己手写 LIKE 全表扫。

## 外部依赖

- OpenAlex：请求带 `OPENALEX_API_KEY`；Crossref 请求带 `OPENALEX_MAILTO` 作为联系信息。两者都要控制频率、加重试，并互为备援。
- Unpaywall：按 DOI 查 OA，仅补合法开放获取链接。
- GROBID：以 Docker 服务方式调用，地址从环境变量读。
- LLM / 嵌入模型：key 从环境变量读，不要硬编码。
- 所有外部依赖写进 `.env.example`，至少包含：`OPENALEX_API_KEY`、`OPENALEX_MAILTO`、`UNPAYWALL_EMAIL`、`GROBID_URL`、`LLM_API_KEY`、`EMBEDDING_MODEL`、`VECTOR_DB_PATH`、`DATABASE_PATH`。

## 红线（不可逾越）

- 不自动爬取或绕过付费墙获取闭源全文；全文获取是人工 + OA 自动补全。
- 化学库导出必须经人工复核闸门：反应集内任一反应未 `verified` 时，`export` 返回 409。
- 速率系数等数值**保留论文原文**，不做自动单位换算、不臆造缺失值。
- 不得用 mock/假数据冒充功能完成；验收标准要求的链路必须真实跑通。

## 完成标准

每个任务交付时：(1) 满足 `docs/任务拆分_开发路线.md` 中该任务的全部验收标准；(2) 本地能 `uvicorn` 起服务并验证（给出 curl 或最小测试）；(3) 不破坏已通过的既有任务。
