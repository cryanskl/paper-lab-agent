# Phase 1 实施报告

> 本报告记录 `paper-lab-agent` Phase 1 最小可运行闭环的实现情况。范围严格遵守 `AGENTS.md` 与 `docs/product-spec.md`,未越界引入 V1 非目标功能。

## 一、目标回顾

实现 V1 最小闭环:

1. 初始化 Next.js + TypeScript + pnpm 项目。
2. SQLite 本地数据层 + 本地 `data/` 文件库约定。
3. Deterministic fake model adapter。
4. 用 `fixtures/intake/arxiv-sample.json` 实现 paper intake fixture import。
5. 用 `fixtures/papers/sample-paper-segments.json` 实现 paper segment 入库。
6. 最小 Paper Library 页面。
7. 最小 Bilingual Reader 页面(左英右中,段落 id 与顺序一致)。
8. 最小 Ask Papers 功能(检索 + citation,无证据返回 `insufficient evidence`)。
9. 最小 Simulation Spec 功能(assumptions / parameters / units / boundary conditions / run steps / artifact paths)。
10. 默认测试无网络、无 LLM,覆盖硬性要求的 5 类断言。

明确不做(对照 V1 Non-Goals):

- 不接真实 OpenAI / Ollama。
- 不做登录态下载。
- 不做完整爬虫。
- 不做完整 PDF 解析。
- 不做云部署、账号系统、团队协作。
- 不删任何已有 `docs/` 与 `fixtures/`。

## 二、新增/修改文件清单

### 根目录配置

| 文件 | 用途 |
| --- | --- |
| `package.json` | 依赖与脚本 |
| `pnpm-lock.yaml` | 锁文件(pnpm 自动生成) |
| `.npmrc` | 允许 `better-sqlite3` 等可信包执行 postinstall |
| `tsconfig.json` | 严格 TypeScript + `@/*` 路径别名 |
| `vitest.config.ts` | Vitest 配置(默认 no-network) |
| `next.config.ts` | Next.js 15,`serverExternalPackages: ["better-sqlite3"]` |
| `next-env.d.ts` | Next.js 类型引用 |
| `.env` | 由 `.env.example` 复制,本地运行配置 |

### 应用代码 `src/`

| 文件 | 职责 |
| --- | --- |
| `src/types/domain.ts` | 核心数据模型:`Paper` / `PaperSegment` / `IntakeRun` / `AssistantAnswer` / `SimulationSpec` 等 |
| `src/lib/config.ts` | 从 env 读取所有路径、provider、fixture 路径 |
| `src/lib/db.ts` | `better-sqlite3` 连接 + schema(3 张表 + 索引)+ 测试 reset 钩子 |
| `src/lib/files.ts` | `data/` 目录布局与路径工具 |
| `src/lib/models/adapter.ts` | `ModelAdapter` 统一接口 |
| `src/lib/models/fake-adapter.ts` | Deterministic fake 实现(translate 走 fixture 中文;relevance 用 keyword 命中;RAG 直接拼接检索段;simulation 输出固定 shape) |
| `src/lib/models/index.ts` | Adapter 工厂(V1 拒绝非 `fake` provider) |
| `src/lib/intake/import-fixture.ts` | 读 intake fixture,跑 fake relevance,落库 + 写 `intake_runs` |
| `src/lib/library/papers.ts` | `listPapers` / `getPaper` / `getTitleByPaperId` |
| `src/lib/library/segments.ts` | 段落实例 upsert(含 paper 占位行,满足 FK)+ list / getAll |
| `src/lib/assistant/answer.ts` | tokenize(英文停用词)+ bigram 加权检索 + fake 生成 answer |
| `src/lib/simulation/build-spec.ts` | 读 method fixture → spec → 落盘到 `data/simulations/` |
| `src/app/layout.tsx` + `globals.css` | 站点壳与样式 |
| `src/app/page.tsx` | Dashboard(总览) |
| `src/app/library/page.tsx` | Paper Library 列表 |
| `src/app/library/[paperId]/page.tsx` | Bilingual Reader(同 `segmentId` 同行左英右中) |
| `src/app/ask/page.tsx` | Ask Papers(支持 `?q=` 提问,展示 answer + citations) |
| `src/app/simulation/page.tsx` | Simulation Spec 渲染 |

### 脚本 `scripts/`

| 文件 | 职责 |
| --- | --- |
| `scripts/import-fixtures.ts` | 一键 import 三份 fixtures + 写 spec.json,idempotent |

### 测试 `tests/`

| 文件 | 测试数 | 覆盖 |
| --- | --- | --- |
| `tests/helpers/setup.ts` | — | 临时数据目录 + fresh DB 的测试工具 |
| `tests/intake.test.ts` | 5 | fixture 导入、id 稳定、relevance rationale、intake run 计数、upsert 去重、library API |
| `tests/bilingual.test.ts` | 3 | 段落导入、双语 1:1 对齐、顺序稳定 |
| `tests/rag.test.ts` | 5 | 3 个 golden questions、`insufficient evidence`、检索排序 |
| `tests/simulation.test.ts` | 3 | fixture 加载、required fields 齐全、artifact path 限定在 `data/simulations/` |

**总计:16 个 test case,全部通过。**

## 三、架构与关键决策

### 数据流

```text
fixtures/intake/*.json
  -> importIntakeFixture()
  -> ModelAdapter.scoreRelevance()  (fake)
  -> SQLite papers + intake_runs

fixtures/papers/*.json
  -> importSegmentsFixture()        (自动 upsert paper 占位行,满足 FK)
  -> SQLite paper_segments

fixtures/rag/golden-questions.json
  -> askQuestion()
  -> retrieveSegments()  (tokenize + bigram 加权)
  -> ModelAdapter.generateAnswer()  (fake,固定 shape)
  -> answer + citations(每条带 paperId + segmentId + paperTitle)

fixtures/simulation/*.txt
  -> buildSimulationSpec()
  -> ModelAdapter.generateSimulationSpec()  (fake,固定 shape)
  -> data/simulations/<paperId>/spec.json
```

### 模块边界(对应 `docs/architecture.md`)

- **Intake**:只负责 fixture/源拉取 + dedup + 状态机,不下结论相关性。
- **Relevance**:通过 `ModelAdapter.scoreRelevance`,由 fake adapter 实现关键字命中,产出 `accepted` / `rejected` + rationale。
- **Library**:其他模块只能通过 `library/papers.ts` / `library/segments.ts` 读写 SQLite。
- **Reader**:`/library/[paperId]` 渲染两列,只依赖 `PaperSegment` 稳定 id。
- **Assistant**:`askQuestion` 调 fake adapter;无命中必须 `insufficientEvidence: true`。
- **Simulation**:`buildSimulationSpec` 产 spec + 落盘;**不**承诺复现 benchmark。
- **Model Adapters**:统一接口,V1 仅 `FakeModelAdapter`,工厂对其他 provider 抛错。

### 关键实现细节

- **RAG 检索**:tokenize 过滤英文停用词(`the` / `of` / `a` 等),保留 CJK 子串匹配;phrase(bigram)权重 = 3 × 单 token,确保 "boundary conditions" 这种短语能稳定击败偶然命中。
- **Bilingual 对齐**:Reader 两列均来自同一 `listPaperSegments(paperId)` 的有序数组,`segmentId` 与 `order` 在两列严格对应;测试断言 `idsEn === idsZh`。
- **fake 翻译**:adapter 的 `translate` 是 passthrough,中文翻译来自 fixture(`sample-paper-segments.json` 是 ground truth)。harness 测的不是模型创意,而是"fixture 中文是否原样入库"。
- **insufficient evidence**:golden 第 3 题问 GPU cluster,fixture 里无该 token 命中,`retrieveSegments` 返回 `[]`,adapter 必返回 `insufficientEvidence: true`、`citations: []`。
- **artifact path 限定**:spec 的 `artifactPaths` 全部以 `data/simulations/` 开头,由 fake adapter 硬编码;测试断言避免 V1 误写出本地数据目录外。

## 四、如何运行

### 启动本地应用

```bash
cd /Users/zenith/Desktop/paper-lab-agent
pnpm install            # 一次性,会编译 better-sqlite3 native binding
pnpm seed               # 把 fixtures 写进 data/paper-lab-agent.sqlite
pnpm dev                # http://localhost:3000
```

可用页面:

- `/` — Dashboard
- `/library` — Paper Library
- `/library/paper-surrogate-sim-001` — Bilingual Reader
- `/ask?q=<question>` — Ask Papers
- `/simulation` — Simulation Spec

### 运行测试与构建

```bash
pnpm typecheck          # tsc --noEmit
pnpm test               # vitest run(无网络、无 LLM)
pnpm test:watch         # vitest
pnpm build              # Next.js 生产构建
```

**当前结果:**

- `pnpm typecheck` ✅
- `pnpm test` 16/16 ✅
- `pnpm build` ✅(5 个 page 全部成功)

## 五、Phase 1 已完成功能

- ✅ Next.js 15 + TypeScript + pnpm 项目初始化
- ✅ SQLite 本地数据层(`better-sqlite3`,3 张表,带 FK + 索引)
- ✅ 本地 `data/` 目录约定(pdf / text / translations / simulations)
- ✅ Deterministic fake model adapter(接口 + 实现 + 工厂)
- ✅ 论文 intake fixture import
- ✅ 论文 segment 入库(含 paper 占位行)
- ✅ Paper Library 页面
- ✅ Bilingual Reader 页面(段落 id 与顺序在两列严格一致)
- ✅ Ask Papers(检索 + 必带 citation,无证据 → `insufficient evidence`)
- ✅ Simulation Spec(assumptions / parameters / units / boundary conditions / run steps / artifact paths)
- ✅ 默认测试无网络、无 LLM,覆盖 5 类硬性断言

## 六、Phase 2 仍待做(明确未做)

按 V1 Non-Goals 与任务硬性不做列表:

- 真实 PDF 解析(PDF → 段落切分 → 翻译流水线)
- 真实 OpenAI / Ollama adapter(目前 factory 拒绝非 `fake` provider)
- 实时 arXiv API 抓取(目前只能 fixture import)
- PDF 下载器(`downloadStatus` 字段已就位但无下载逻辑)
- 登录态下载(allowlist env 已留位,无实现)
- Sources & Profile 配置页(目前只能改 env)
- SQLite FTS5 全文索引(目前 JS 端 tokenize 检索)
- Schedule entry / 计划任务(launchd / cron)
- Lab 可运行 artifact(spec 已生成,但没真的写 Python / notebook / chart)
- 集成测试套件(目前只有 unit)
- Cloud / 账号 / 团队协作(明确非目标)
- 浏览器视觉验证(本会话无 Chrome MCP 工具,仅 `curl` 验证 5 个页面 200 + 关键内容存在;建议人工浏览器复检)

## 七、Git 状态

按 `AGENTS.md` 的 Git Safety 规则:

- 当前在 `main` 分支,`git rev-parse --show-toplevel` = 当前 worktree。
- **未** 执行 `git add` / `commit` / `push` — 任务只要求"完成后运行 pnpm build 和测试命令"并汇报,等待用户审阅后再决定是否提交。
- 已确认 `.gitignore` 覆盖 `node_modules/`、`.next/`、`data/`、`*.sqlite`、`.env`,无敏感信息泄露风险。
