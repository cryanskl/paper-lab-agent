# paper-lab-agent

低温等离子体文献检索与理解系统。V1 采用 local-first 架构：FastAPI + SQLite + APScheduler + GROBID + Chroma/FAISS 兼容的本地索引约定，前端使用 Streamlit。

当前版本：`0.1.0`

## Quick Start

一键启动（推荐给本机演示或日常点击启动）：

```bash
./start.sh
```

`start.sh` 会自动创建 `.env`（如果不存在）、创建或复用 `.venv`、安装 `requirements.txt` 里的后端和 Streamlit 前端依赖、检查并释放 FastAPI/Streamlit 端口、启动前后端、等待健康检查通过后打开前端网页。每次运行都会写入独立日志目录：`logs/run-YYYYMMDD-HHMMSS/startup.log`、`backend.log`、`frontend.log`。需要只验证启动不打开浏览器时可运行：`START_OPEN_BROWSER=false DEV_EXIT_AFTER_READY=true ./start.sh`。

手动启动：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/doctor.py --compact
cp .env.example .env
bash scripts/dev.sh
```

服务启动时会自动用 `docs/schema.sql` 初始化 `data/plasma.db`。
`scripts/doctor.py --compact` 会在启动服务前检查 Python 版本、关键项目文件、Python 依赖是否可导入、本地存储目录可创建和可写，以及外部能力配置 warning；它会读取 `.env` 中的本地路径配置，但已导出的环境变量仍优先，适合新机器快速预检。compact 输出里的 `warning_count`、`warning_codes` 和 `warning_details` 用于提示 OpenAlex、Unpaywall、LLM 等可选外部能力是否未配置，也会提示 `unsupported_embedding_model`、`unsupported_vector_db_backend` 这类 RAG 配置风险。发布、演示或交付前请使用 `python scripts/doctor.py --strict --compact`，让必需检查失败时返回非零退出码；release gate 固定验证正式的 `bge-m3 + Chroma` 索引契约，不再切换到旧哈希索引。
`scripts/dev.sh` 会等待 FastAPI `/api/v1/health` 和 Streamlit `/_stcore/health` 都可访问后再打印地址。
如果只设置 `PAPER_LAB_DATA_DIR`，SQLite、PDF、TEI、翻译、导出和本地向量索引默认都会落在该目录下；需要拆分存储位置时再单独设置 `DATABASE_PATH`、`PAPER_LAB_PDF_DIR`、`VECTOR_DB_PATH` 等变量。

OpenAlex 正式调用需要免费 API Key。在 <https://openalex.org/settings/api> 注册并复制 Key 后，将其写入本地 `.env` 的 `OPENALEX_API_KEY`；`OPENALEX_MAILTO` 保留为 Crossref/OpenAlex 的联系邮箱。Unpaywall 无需单独注册账号，只需设置 `UNPAYWALL_EMAIL`。系统状态只暴露这些配置是否存在，不返回凭据内容。

验证：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/system/status
curl 'http://127.0.0.1:8000/api/v1/journals?active=true'
python scripts/health_check.py
python scripts/health_check.py --compact
python scripts/health_check.py --summary-only --compact
python scripts/health_check.py --summary-only --compact --output out/health-summary.json
python scripts/health_check.py --require-storage-writable
python scripts/health_check.py --require-no-failed-workflows
python scripts/health_check.py --require-no-config-warnings
python scripts/health_check.py --require-demo-data
python scripts/health_check.py --require-release-ready
python scripts/health_check.py --check-frontend
python scripts/health_check.py --require-frontend
python scripts/health_check.py --check-frontend --frontend-url http://127.0.0.1:8501
python scripts/health_check.py --check-openapi
python scripts/health_check.py --require-openapi
curl http://127.0.0.1:8000/openapi.json
API_BASE_URL=http://127.0.0.1:8001/api/v1 python scripts/health_check.py
```

`/api/v1/system/status` 会返回 `config_warnings`，用于提示 OpenAlex、Unpaywall、LLM 等可选外部能力是否还未配置；这些可选能力缺失不会阻断基础发布就绪。对于 unsupported RAG adapter 这类配置风险，warning 会带上 `actual` 和 `supported`，直接展示当前配置值和本版本支持列表。
同一响应里的 `release_readiness` 会汇总演示数据、失败工作流、配置 warning 和存储可写性；`demo_data_missing`、`failed_workflows` 和 `storage_errors` 会阻断发布就绪状态，`config_warning_codes` 只提示可选外部能力缺失。`python scripts/health_check.py --summary-only --compact` 与 `--require-release-ready` 都会优先使用这个 API 聚合结果输出或阻断发布就绪状态。compact summary 会额外给出 `workflows_ok`、`config_ready` 和 `release_blockers`，便于快速判断是任务失败、配置未完成还是存储/演示数据阻断。
同一响应里的 `translation_adapter` 和 `llm_model` 会说明当前翻译链路使用本地 `local-echo` 还是 `openai-compatible`，`python scripts/health_check.py` 会把这两个字段作为发布健康契约校验。

导出 OpenAPI JSON 给前端、评审或发布流程使用时，不启动服务也可以生成当前接口 schema：

```bash
python scripts/export_openapi.py --output out/openapi.json
python scripts/build_release_handoff.py --artifact-dir out/release --package out/paper-lab-agent-release.zip --compact
python scripts/export_release_artifacts.py --output-dir out/release --compact
python scripts/validate_release_artifacts.py --artifact-dir out/release --compact
python scripts/package_release_artifacts.py --artifact-dir out/release --output out/paper-lab-agent-release.zip --compact
python scripts/validate_release_package.py --package out/paper-lab-agent-release.zip --compact
```

`scripts/build_release_handoff.py` 是正式交接的单命令入口，会依次导出 artifact、校验 artifact、打包 zip、复验 zip，并输出最终交接报告；如果需要定位某一步问题，可继续使用下面四条分步命令。`scripts/export_release_artifacts.py` 会一次性生成 `openapi.json`、`demo-summary.json`、`release-acceptance-matrix.md` 和 `release-manifest.json`，用于前后端、评审或发布交接。manifest 会记录来源 git commit/branch、导出时 worktree 是否 dirty、`artifact_count`、`artifact_names`，以及四个文件的 SHA256 校验和；同时会透传 doctor preflight 结果，包括 `preflight_warning_codes` 和 `preflight_warning_details`。`scripts/validate_release_artifacts.py` 会校验 artifact 路径本身是否为目录、交接包文件是否齐全、是否可读取、是否包含额外文件、校验和是否匹配、版本是否一致、演示摘要是否 ready、preflight 证据是否完整、验收矩阵是否与 `docs/release-acceptance-matrix.md` 逐字一致并包含 PRD/schema/release gate 关键信息，以及 OpenAPI 是否包含基础路径、`system` tag metadata 和 `ErrorResponse` schema。`scripts/package_release_artifacts.py` 会先校验目录，再打包为单个 zip，并输出 `artifact_count`、`artifact_names`、包的 SHA256、demo readiness、导出格式、`demo_export_audit_entry_counts`、`reaction_set_verified_by`、`reaction_set_verified_at`、`preflight_warning_codes` 和 `preflight_warning_details`；zip 输出路径必须放在 artifact 目录外，避免覆盖或污染 handoff 文件。`scripts/validate_release_package.py` 会校验 zip 内 artifact 条目是否为普通文件、是否存在不安全路径或 symlink，然后解压并复验 zip 内 artifacts，防止交接文件被篡改或缺项，并在报告中透传同一组 demo 与 preflight 证据。正式交接前可追加 `--require-clean-source`，要求 manifest 里的 `source.git_dirty=false`。服务启动后也可以直接访问 live schema 与交互文档：`http://127.0.0.1:8000/openapi.json`、`http://127.0.0.1:8000/docs` 和 `http://127.0.0.1:8000/redoc`。`python scripts/health_check.py --check-openapi` 会探测 live `/openapi.json` 并校验基础 schema 契约；`--require-openapi` 会在 schema 不可访问或缺少必需路径、tag、错误响应模型时返回非零。

导入离线样例论文和 PDF 文档：

```bash
python scripts/import_fixtures.py
python scripts/prepare_demo_data.py
python scripts/prepare_demo_data.py --compact
python scripts/prepare_demo_data.py --summary-only --compact
python scripts/prepare_demo_data.py --summary-only --compact --output out/demo-summary.json
python scripts/health_check.py --require-demo-data
curl 'http://127.0.0.1:8000/api/v1/papers?q=plasma'
curl 'http://127.0.0.1:8000/api/v1/documents'
```

`scripts/import_fixtures.py` 只导入论文和 PDF fixture；`scripts/prepare_demo_data.py` 会继续跑解析、索引、翻译、化学抽取、人工复核标记和三种导出，适合正式演示前一次性准备 walking skeleton 数据。`--compact` 会输出单行完整 JSON，可看 `summary.ready`；`--summary-only --compact` 只输出发布摘要，可直接看顶层 `ready`、`export_formats`、`export_audit_entry_counts` 和核心状态字段；加 `--output out/demo-summary.json` 可生成发布交接用摘要 artifact。

启用定时抓取：

```bash
PAPER_LAB_SCHEDULER_ENABLED=true bash scripts/dev.sh
```

默认关闭 scheduler，避免本地隔离测试和首次启动时自动访问外部 API。启用后可在 Streamlit 侧边栏或 `/api/v1/system/status` 的 `runtime.scheduler_enabled` 确认状态；`runtime.scheduler_jobs` 会列出 daily / weekly / monthly 抓取计划和 UTC 触发时间。

## Backend Only

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## macOS / Windows

同一套代码在两个系统上跑；只有启动脚本分平台，应用本身没有平台分支。

| | macOS / Linux | Windows |
| --- | --- | --- |
| 一键启动 | `bash start.sh` | `powershell -ExecutionPolicy Bypass -File .\start.ps1` |
| 虚拟环境解释器 | `.venv/bin/python` | `.venv\Scripts\python.exe` |

两个脚本读同一批环境变量（`API_HOST`、`API_PORT`、`STREAMLIT_PORT`、`START_OPEN_BROWSER`、
`DEV_READY_TIMEOUT`、`PAPER_LAB_SCHEDULER_ENABLED`、`LOG_DIR` 等），行为与输出对齐，
都会打印 FastAPI / 工作台 / Streamlit 三个地址并默认打开工作台。

Windows 相关注意事项：

- 中文版 Windows 的默认 ANSI 代码页是 GBK。`start.ps1` 会固定 `PYTHONUTF8=1` 与
  `PYTHONIOENCODING=utf-8` 并按 UTF-8 读 `.env`，避免中文日志和配置乱码。应用代码里所有文件
  读写都显式带 `encoding="utf-8"`，`tests/test_web_ui.py` 有回归守卫防止漏写。
- 存储路径全部走 `pathlib` 并从环境变量读，`.env` 里用 `./data/...` 这种相对路径在两个系统上都可用。
- GROBID 仍以 Docker 服务方式调用，地址从 `GROBID_URL` 读，与宿主系统无关。
- 前端是浏览器页面，不依赖宿主系统。

## 文献工作台（Web UI）

工作台随 API 一起提供，无需单独进程、无需构建步骤：起好 uvicorn 后打开 <http://127.0.0.1:8000/>
即自动跳转到 `/ui/`。静态资源在 `web/`（原生 HTML + CSS + JS，不引入前端框架，也不加载任何 CDN），
由 FastAPI 的 `StaticFiles` 直接挂载在 `/ui`。

工作台页面对应后端既有能力与本地阅读工具：

| 页面 | 主要动作 | 依赖接口 |
| --- | --- | --- |
| 文献检索 | 期刊只限定来源；搜索栏支持逗号分隔词/短语、OR/AND 和 20/50/100 篇全局上限。联网模式汇总全部期刊候选后按相关性与期刊轮转公平选取，失败时回退 Crossref，并补齐可获得的摘要；24 小时内精确重复查询直接复用本地结果。作者与 DOI 也可本地检索 | `GET /papers`、`POST /crawl/run`、`POST /crawl/searches/{id}/save`、`DELETE /crawl/searches/{id}`、`GET /crawl/jobs/{id}` |
| 文献库 | 拖拽上传 PDF、合法 OA PDF 后台下载、触发解析 / 翻译 / RAG 索引 / 化学库抽取、给文献打标、查看状态与失败原因 | `POST /documents`、`POST /papers/{id}/download`、`POST /documents/{id}/parse`、`.../translate`、`.../index`、`.../extract-chemistry`、`PUT /papers/{id}/categories` |
| 下载管理 | 查看 OA 下载任务、进度与失败原因，并从本地安全打开已完成文件 | `GET /paper-downloads`、`GET /documents/{id}/file` |
| 术语表管理 | 在 SQLite 中维护中英术语；阅读页选词可直接加入，正文高亮即时更新；旧版浏览器术语首次打开时自动迁移 | `GET/POST/PUT/DELETE /glossary-terms`、`POST /term-translations` |
| 双语阅读 | 左右分栏对照、滚动联动、字号调节、术语高亮、划选发送到问答 | `GET /documents/{id}/sections`、`GET /documents/{id}/translation` |
| AI 问答 | 单篇 / 项目 / 全库范围检索；单篇问答可直接使用已解析文档上下文，索引检索支持跨语言 embedding，回答带 `[n·¶段]` 引用并可点击跳回原文 | `POST /rag/query` |
| 化学库复核 | 逐条人工复核（复核人必填、可顺手修正字段）、看原文出处与审计日志、闸门通过后导出仿真输入 | `GET /reaction-sets/{id}`、`PUT /reactions/{id}/verify`、`POST /reaction-sets/{id}/export` |

**打标**复用既有 taxonomy：文献库卡片上勾选标签写入 `paper_categories`（`method=manual`），
可新建标签，也可调 LLM 自动分类；标签同时作为检索页的筛选条件。未关联 `paper` 的文档不能打标，
界面会如实说明原因，而不是静默失败。

**化学库复核**是交付物的最后一关。速率系数与阈值一律保留论文原文，界面不做单位换算、不填补缺失值；
反应集内任一反应未 `verified` 时导出返回 409，工作台会把这条闸门原因直接显示出来——闸门不可绕过。

「项目分组」和「阅读偏好」仍是浏览器本地状态。术语表与下载任务已经写入 SQLite，便于跨页面复用和
追踪状态；旧版 `localStorage` 术语只做一次兼容迁移。全文获取仍坚持人工上传 + 合法 OA 自动补全，
下载器只使用已核验的开放获取链接，不会爬取或绕过付费墙。

未配置 `LLM_API_KEY` 时翻译走本地 echo adapter，但回显只作为诊断结果；工作台会标记「仅原文·请重译」，
不会把原文冒充成译文。

联网搜索在未选择单本期刊时会覆盖全部 active 白名单期刊，并默认同时处理 3 本；可通过 `.env` 的 `CRAWL_MAX_CONCURRENCY=1..10` 调整。后端会等待所有期刊候选完成，再按“期刊内相关性排序 + 跨期刊轮转”填充全局 20/50/100 篇配额，避免响应最快的期刊垄断结果。OA 补全只对进入配额的结果执行，精确重复查询缓存 TTL 为 24 小时。前端最多等待 30 分钟并持续显示完成数，等待超时只停止页面轮询，不会取消后端已经创建的搜索任务。

默认使用 `EMBEDDING_MODEL=bge-m3`、`VECTOR_DB_BACKEND=chroma` 和目录型 `VECTOR_DB_PATH=data/chroma`，
用于中文问题跨语言检索英文论文。旧的 `local-hash/local-json` 仅保留为历史索引迁移诊断兼容，不再作为
产品默认或发布验收路径；从旧配置切换后必须重新索引已有文档，避免新旧向量维度混用。

## Streamlit

Streamlit 页面继续保留，作为面向发布验收的运维视图（抓取任务诊断、化学库复核、release readiness）。

```bash
python -m streamlit run streamlit_app.py
```

默认前端连接 `http://127.0.0.1:8000/api/v1`。如需修改：

```bash
API_BASE_URL=http://127.0.0.1:8000/api/v1 python -m streamlit run streamlit_app.py
```

## Optional GROBID

GROBID 只在解析真实 PDF 时需要。隔离测试和本地文本 fallback 不依赖它。
`--check-external` 会主动检查 GROBID；默认健康检查不访问外部服务。

```bash
docker run --rm -p 8070:8070 lfoppiano/grobid
python scripts/health_check.py --check-external
python scripts/health_check.py --require-grobid
```

`--require-grobid` 会主动检查 GROBID，并在不可用时返回非零退出码，适合真实 PDF 解析部署前的强制门禁。

## Verification

```bash
python scripts/doctor.py --strict --compact
bash scripts/release_check.sh
```

这两条命令会执行与 CI 相同的正式索引发布检查：先用 strict doctor 阻断缺失依赖或关键文件，再校验启动脚本语法、`git diff --check`、`git diff --cached --check`、编译关键脚本、检查 scripts 目录下所有 Python 脚本的 `--help` 入口以提前发现 CLI 参数或 import path 问题。release gate also starts a live API with prepared demo data and runs `scripts/health_check.py --require-release-ready` before running the full test suite.
发布或演示前的完整检查顺序见 [docs/release-checklist.md](docs/release-checklist.md)。

`python scripts/health_check.py --check-frontend` 会额外探测 Streamlit `/_stcore/health`，用于确认 `scripts/dev.sh` 启动后的后端和前端都可访问。
`python scripts/health_check.py --summary-only --compact` 会输出短摘要，包含 `release_ready`、`release_blockers`、`api_status`、`demo_data_ready`、`failed_workflows`、`workflows_ok`、`config_warning_count`、`config_ready`、`config_warning_codes`、`config_warning_details`、`scheduler_enabled`、`scheduler_job_count`、`scheduler_job_ids`、`storage_writable`、`storage_errors` 和 `storage_health`，适合发布或演示前快速确认 live 环境；搭配 `--check-frontend` 时还会返回 `frontend_ok`、`frontend_status_code` 和 `frontend_url`，搭配 `--check-openapi` 时还会返回 `openapi_ok`、`openapi_path_count` 和 `openapi_tag_names`，搭配 `--check-external` 时还会返回 `grobid_available`、`grobid_status_code`、`grobid_url` 和 `grobid_error`。如果这些显式探测失败，`release_blockers` 也会追加 `frontend:*`、`openapi:*` 或 `grobid:*` 阻断项。
`python scripts/health_check.py --require-frontend` 会主动探测 Streamlit，并在前端健康探针不是 200 时返回非零，适合 `scripts/dev.sh` 启动后做发布或演示前门禁。
`python scripts/health_check.py --require-openapi` 会主动探测 live `/openapi.json`，并在 OpenAPI schema 不可访问或基础契约不完整时返回非零，适合接口交付或前端联调前门禁。
`python scripts/health_check.py --require-storage-writable` 会在数据目录、PDF/TEI/翻译/导出目录、数据库父目录或向量索引父目录不可写，或已存在的本地向量索引 JSON 损坏时返回非零，适合发布前预检本机运行环境。
`python scripts/health_check.py --require-no-failed-workflows` 会在抓取、解析、索引、翻译、化学抽取或反应集复核状态统计中存在 `failed`、`rejected` 或 `unknown` 项时返回非零，适合部署前确认没有已知失败、拒绝或未知状态积压。
`python scripts/health_check.py --require-no-config-warnings` 会在 OpenAlex、Unpaywall、LLM、向量后端等配置告警存在时返回非零，适合正式演示或部署前确认外部能力已按预期配置。
`python scripts/health_check.py --require-demo-data` 会在 live API 的 `counts` 缺少期刊、论文、文档、章节、chunk、反应集或反应样例时返回非零，适合正式演示前确认 walking skeleton 数据已准备好。
`python scripts/health_check.py --require-release-ready` 会组合 storage writable、no failed workflows 和 demo data 三个基础门禁；外部能力配置用 `--require-no-config-warnings` 按需单独强制，前端和 GROBID 仍用 `--require-frontend`、`--require-grobid` 按需单独强制。
`DEV_EXIT_AFTER_READY=true bash scripts/dev.sh` 会在 API 和 Streamlit 都 ready 后退出并清理子进程，适合 CI 或发布前验证统一启动命令本身。

如需只跑隔离的 walking skeleton smoke：

```bash
python -m scripts.smoke_check
```

该 smoke 会在临时目录初始化空库、导入 fixture 论文、验证 `/papers` 检索，并以正式的 `bge-m3 + Chroma` 契约跑通 PDF fallback 的上传、解析、索引、RAG 查询，以及翻译、化学抽取、复核闸门和导出；为保证测试可复现，它不访问外部服务。输出 JSON 会包含 `config_warning_count`、`config_warning_codes` 和 `config_warning_details`，用于确认隔离 smoke 允许的可选外部能力缺口。

如需只跑测试：

```bash
python -m pytest -q
```

默认测试使用临时 SQLite 数据库和本地 fixture，不依赖外部网络、GROBID 或真实模型。

CI 配置在 `.github/workflows/ci.yml`，默认跑同一条隔离测试命令；GitHub Actions 也支持 `workflow_dispatch`，可在发布或演示前手动触发 release gate。

## Troubleshooting

- API 端口冲突：`API_PORT=8001 bash scripts/dev.sh`
- Streamlit 端口冲突：`STREAMLIT_PORT=8502 bash scripts/dev.sh`
- 慢机器启动超时：`DEV_READY_TIMEOUT=60 bash scripts/dev.sh`
- 指定解释器：`PYTHON=.venv/bin/python bash scripts/dev.sh`
- GROBID 未启动：解析会降级为本地文本 fallback，`documents.parse_error` 会记录原因。
- 外部 API 未配置：OpenAlex 从 `.env` 读取 `OPENALEX_API_KEY`，Unpaywall 读取 `UNPAYWALL_EMAIL`，LLM 读取 `LLM_API_KEY`；未配置时系统保持本地可运行，不用假数据冒充外部能力。

## Productization Roadmap

成品化阶段见 [docs/productization-roadmap.md](docs/productization-roadmap.md)。
发布验收矩阵见 [docs/release-acceptance-matrix.md](docs/release-acceptance-matrix.md)。
