# 本机科研助手全平台 V1 计划

## Summary

分类：**功能/重构**。这是从空目录开始的新产品设计，包含论文抓取、双语阅读、全库 RAG 问答、物理/工程仿真实验助手四个模块。

V1 采用 **Next.js 模块化单体 + SQLite + 本地文件库**。先跑通完整产品闭环，模型层先用 fake adapter，后续替换为 Ollama 或其他本地模型服务。

## Key Changes

- 建立本机 Web 应用：`Dashboard`、`Sources & Profile`、`Paper Library`、`Paper Reader`、`Research Assistant / Lab`。
- 论文来源优先支持 arXiv/RSS/API/期刊检索接口；相关性用“关键词 + 种子论文”配置。
- 数据库存储论文元数据、筛选状态、下载状态、段落、翻译、问答引用、实验产物索引；PDF/文本/实验文件存在本地文件夹。
- 双语阅读采用段落级左右对照：左英文原文，右中文翻译。
- RAG 问答默认检索所有已抓论文，回答必须带论文标题和段落引用。
- 实验助手先做物理/工程 **toy simulation**：输出假设、参数、单位、边界条件、可运行示例和动画/图表讲解，不承诺完整复现论文 benchmark。
- 登录态下载作为受控 adapter：仅 allowlist 域名启用，不保存密码，不绕过验证码；失败写明原因。

## Public Interfaces / Types

- `ResearchProfile`：来源列表、关键词、种子论文、下载 allowlist、计划任务配置。
- `Paper`：标题、作者、摘要、来源、URL、PDF 路径、状态、相关性理由。
- `PaperSegment`：paper id、段落序号、英文文本、中文翻译、页码/位置、embedding/FTS 索引字段。
- `IntakeRun`：运行时间、来源、候选数、接受数、拒绝数、下载失败数、错误日志。
- `AssistantAnswer`：用户问题、检索段落、回答文本、引用列表、证据不足标记。
- `SimulationSpec`：论文方法来源、物理/工程假设、参数、单位、边界条件、运行步骤、产物路径。

## Implementation Plan

1. 初始化 Next.js + TypeScript + pnpm 项目，使用 SQLite 数据库和本地 `data/` 文件库。
2. 建立 schema 和数据访问层，优先支持论文、段落、任务日志、问答引用、实验产物。
3. 实现 Sources/Profile 页面和 arXiv/API intake runner，支持手动触发。
4. 实现相关性筛选 pipeline：关键词初筛 + fake model adapter 复筛。
5. 实现 PDF 下载器：开放 PDF 直接下载，allowlist 登录态 adapter 先保留接口和失败记录。
6. 实现 PDF 文本解析、段落切分、fake 翻译、SQLite FTS 检索。
7. 实现论文库和段落级双语 Reader。
8. 实现全库 Ask Papers：检索段落、生成 fake 回答、展示引用。
9. 实现 Experiment Lab：从论文段落生成 simulation spec、最小 Python/Notebook artifact 和图表/动画占位。
10. 增加任务日志、错误状态、基础设置和计划任务命令入口。

## Test Plan

- Intake：arXiv/API mock 返回候选论文后，去重、入库、状态正确。
- Relevance：关键词命中、种子论文相似输入、拒绝样本都产生可解释理由。
- Download：开放 PDF 成功保存；登录/付费/验证码页面记录失败原因。
- Reader：同一段英文和中文翻译能稳定左右对齐。
- RAG：回答只基于检索到的段落，并展示论文标题和段落引用；无证据时返回证据不足。
- Simulation：物理/工程实验 spec 必须包含假设、参数、单位、边界条件和可运行产物路径。
- Build：每次改动后跑 `pnpm build`；涉及 UI 后用浏览器验证主要页面。

## Assumptions

- 第一阶段本机私有运行，不做账号系统、云同步、团队协作。
- 模型层先用 fake adapter，保证产品数据流和 UI 可运行；本地模型接入作为后续阶段。
- 定时任务先提供手动触发和稳定 CLI/route 入口，后续再接 macOS `launchd`。
- “尽量下载 PDF”不包含绕过访问控制；登录态下载仅限用户明确 allowlist 的合法访问来源。
