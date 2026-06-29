# AGENTS.md

> 给 AI 编码 agent 的项目入口说明。每次开始任务前先读本文件；如果本文件与用户当前消息冲突，以用户当前消息为准。

## 开始任务时先做

- 先把任务分类为「小修复」或「功能/重构」，并简短说明理由。
- 非平凡功能、重构、跨多文件改动：走 brainstorm -> spec -> plan -> subagent 驱动实现。
- 小 bug 修复、小文档更新、单文件少量改动：直接做定向修复，不必额外拉长流程。
- 写操作前确认当前 checkout：`git branch --show-current && git rev-parse --show-toplevel`。发现多 worktree 或任务目标不明确时，先停下来确认。
- 每次改动后至少跑与改动相称的检查；发布、演示、接口或数据契约相关改动优先跑 `bash scripts/release_check.sh`。

## 项目一句话

`paper-lab-agent` 是一个 local-first 的低温等离子体文献检索与理解系统：确定性检索层按白名单 ISSN + 关键词抓取论文元数据，大模型/本地 adapter 层负责分类、翻译、RAG、化学反应抽取与可审计导出。V1 当前重点是成品化、发布就绪和交接材料 hardening。

## 当前包含什么

- FastAPI 后端：统一挂在 `/api/v1`，另有 `/health` 和 `/api/v1/health`。
- SQLite 数据库：启动时按 `docs/schema.sql` 初始化，包含期刊、论文、分类、抓取任务、文档、章节、chunks、反应集、审计与导出等表。
- 文献检索链路：期刊白名单 CRUD、OpenAlex/Crossref 元数据抓取、关键词过滤、DOI/无 DOI 去重、Unpaywall OA 补全、FTS5 检索。
- 文档理解链路：PDF 上传、哈希去重、GROBID TEI 解析优先、本地 fallback、章节入库、公式保护翻译、索引和 RAG 查询。
- 化学库链路：从章节/表格抽取反应集，保留来源、速率值、阈值、LXCat URL，人工复核后导出 JSON/TXT/BOLSIG。
- Streamlit 前端：`streamlit_app.py` 通过 `app/frontend_api.py` 调用后端，覆盖检索、抓取、文档、RAG、化学复核、配置和发布就绪状态。
- 调度器：APScheduler，可通过 `PAPER_LAB_SCHEDULER_ENABLED=true` 启用 daily/weekly/monthly crawl。
- 本地演示与交接：fixture/demo data、health check、OpenAPI 导出、release artifacts、handoff zip 和 release gate 脚本。

## 架构地图

- `app/main.py`：FastAPI app 工厂、lifespan、OpenAPI tag、router 注册。
- `app/routers/`：HTTP API 层。
  - `app/routers/system.py`：运行状态、配置 warning、storage health、release readiness。
  - `app/routers/journals.py` / `app/routers/categories.py` / `app/routers/papers.py`：白名单、分类、论文检索、OA、人工分类。
  - `app/routers/crawl.py`：抓取任务创建、后台执行和诊断。
  - `app/routers/documents.py`：上传、解析、翻译、索引、化学抽取。
  - `app/routers/rag.py`：RAG 查询。
  - `app/routers/reactions.py`：反应复核、反应集详情和导出。
- `app/services/`：业务逻辑层。
  - `app/services/crawl.py`：OpenAlex/Crossref 编排、关键词过滤、去重、OA 补全。
  - `app/services/documents.py`：上传保存、GROBID/TEI 解析和 fallback。
  - `app/services/translation.py`：公式掩码、翻译 job、输出路径。
  - `app/services/rag.py`：本地 embedding/vector store adapter、索引和查询。
  - `app/services/chemistry.py`：反应抽取、复核、导出。
  - `app/services/classification.py` / `app/services/llm.py`：分类和 LLM adapter。
- `app/clients/`：OpenAlex、Crossref、Unpaywall、GROBID 客户端和 retry-after 处理。
- `app/db.py`：SQLite 连接、schema 初始化、`PRAGMA foreign_keys=ON`。
- `app/config.py`：`.env` / 环境变量配置、存储目录派生、安全路径检查。
- `app/release_readiness.py`：发布就绪阻断规则。
- `app/scheduler.py`：APScheduler job 注册。
- `scripts/`：本地开发、验证、发布、交接命令入口。
- `tests/`：离线 pytest 覆盖 API、客户端、文档、RAG/embedding、前端 API 和 release contracts。

## 资料在哪

- 产品范围：`docs/PRD_等离子体文献系统.md`。
- 开发顺序与验收：`docs/任务拆分_开发路线.md`。
- API 契约：`docs/接口设计文档.md`。不要自创端点、路径、方法或响应结构。
- 数据模型真理来源：`docs/schema.sql`。不得直接在代码里绕过 schema 增表或改字段。
- 当前成品化路线：`docs/productization-roadmap.md`。
- 发布验收矩阵：`docs/release-acceptance-matrix.md`。
- 发布前检查清单：`docs/release-checklist.md`。
- bug / hardening 记录：`docs/bug/`，新增回归修复时按现有格式补充。
- 环境变量样例：`.env.example`。
- 用户入口和常用命令：`README.md`。

## 常用命令

```bash
./start.sh
```

一键创建/复用 `.venv`、安装 `requirements.txt`、准备 `.env`、释放端口、启动 FastAPI + Streamlit、等待健康检查并打开前端。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/doctor.py --compact
bash scripts/dev.sh
```

手动开发启动。

```bash
python scripts/doctor.py --strict --compact
bash scripts/release_check.sh
python -m pytest -q
```

主要验证入口。`scripts/release_check.sh` 是发布/演示前的默认离线 gate，会覆盖 doctor、脚本/文档/schema/API/env/requirements 校验、dev 启动路径、demo data、live API release readiness、smoke 和全量测试。

```bash
python scripts/prepare_demo_data.py --summary-only --compact
python scripts/health_check.py --summary-only --compact
python scripts/health_check.py --require-release-ready
python scripts/health_check.py --require-frontend
python scripts/health_check.py --require-openapi
```

演示或 live runtime 验证。

```bash
python scripts/build_release_handoff.py --artifact-dir out/release --package out/paper-lab-agent-release.zip --compact
```

生成正式交接包，包含 `openapi.json`、`demo-summary.json`、`release-acceptance-matrix.md`、`release-manifest.json`。

## 环境与存储

- 依赖入口是 `requirements.txt`，当前没有 `pyproject.toml`。
- 配置从 `.env` 和环境变量读取；已导出的环境变量优先。
- 默认本地数据在 `data/`：SQLite、PDF、TEI、翻译、导出和本地向量索引都会派生到该目录。
- 如只想换数据根目录，设置 `PAPER_LAB_DATA_DIR`；需要拆分时再单独设置 `DATABASE_PATH`、`PAPER_LAB_PDF_DIR`、`PAPER_LAB_TEI_DIR`、`PAPER_LAB_TRANSLATION_DIR`、`PAPER_LAB_EXPORT_DIR`、`VECTOR_DB_PATH`。
- 外部能力：`OPENALEX_MAILTO`、`UNPAYWALL_EMAIL`、`GROBID_URL`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`、`EMBEDDING_MODEL`、`VECTOR_DB_BACKEND`。
- 默认离线模式允许 OpenAlex、Unpaywall、LLM、GROBID 未配置，但会在 doctor、system status 和 health summary 里产生 warning。

## 编码与契约规则

- 响应统一 JSON；列表统一 `{items,total,page,page_size}`；错误统一 `{error:{code,message}}` 加语义化 HTTP 状态码。
- 耗时操作用 FastAPI `BackgroundTasks`，立即返回 job/resource 状态，由 status 字段轮询；不要改成同步阻塞。
- 日期统一 ISO8601 文本；多值字段统一存 JSON 文本。
- SQLite 连接必须开启 `PRAGMA foreign_keys=ON`。
- 检索使用已有 `papers_fts`，不要新增 LIKE 全表扫描。
- 外部 API 请求要带 polite pool mailto/email、频率控制和重试；OpenAlex/Crossref 互为备援。
- 不自动爬取或绕过付费墙获取闭源全文；全文来源限人工上传和合法 OA 补全。
- 化学库导出必须经过人工复核闸门：反应集内任一反应未 `verified` 时导出返回 409。
- 速率系数、阈值、截面等数值保留论文原文，不自动单位换算，不臆造缺失值。
- 不得用 mock/假数据冒充功能完成；验收要求的链路必须真实跑通。

## Git 与破坏性操作

- commit 前必须再次运行：

```bash
git branch --show-current
git rev-parse --show-toplevel
git status --short
git diff --check
git diff --cached --check
```

- 破坏性操作必须有用户当前消息明确授权：`reset --hard`、`push --force`、`branch -D`、`clean -f`、`checkout --`、无 WHERE 的批量 DB update/delete、`drop`、`truncate`、`rm -rf`、覆盖未提交修改。
- pre-commit hook 失败后不要用 `--amend` 补救；hook 失败表示新 commit 没发生，修好后重新 add 并创建新 commit。
- 可能存在并行会话时，不要碰无关文件；如果发现用户或其他 agent 的改动，先判断是否影响当前任务，不能擅自回滚。

## 完成标准

- 满足对应任务或用户请求的验收点。
- 运行与改动相称的检查，并在回复中说明实际跑了什么。
- 涉及 UI 时用浏览器验证可见行为；仅脚本成功不等于 UI 验收完成。
- 涉及发布、演示、接口或交接时，优先用 `docs/release-checklist.md` 里的 gate 闭环。
