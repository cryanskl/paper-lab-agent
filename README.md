# paper-lab-agent

低温等离子体文献检索与理解系统。V1 采用 local-first 架构：FastAPI + SQLite + APScheduler + GROBID + Chroma/FAISS 兼容的本地索引约定，前端使用 Streamlit。

当前版本：`0.1.0`

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/doctor.py --compact
cp .env.example .env
bash scripts/dev.sh
```

服务启动时会自动用 `docs/schema.sql` 初始化 `data/plasma.db`。
`scripts/doctor.py --compact` 会在启动服务前检查 Python 版本、关键项目文件、Python 依赖是否可导入，以及本地存储目录可创建和可写；它会读取 `.env` 中的本地路径配置，但已导出的环境变量仍优先，适合新机器快速预检；发布、演示或交付前请使用 `python scripts/doctor.py --strict --compact`，让必需检查失败时返回非零退出码。
`scripts/dev.sh` 会等待 FastAPI `/api/v1/health` 和 Streamlit `/_stcore/health` 都可访问后再打印地址。
如果只设置 `PAPER_LAB_DATA_DIR`，SQLite、PDF、TEI、翻译、导出和本地向量索引默认都会落在该目录下；需要拆分存储位置时再单独设置 `DATABASE_PATH`、`PAPER_LAB_PDF_DIR`、`VECTOR_DB_PATH` 等变量。

验证：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/system/status
curl 'http://127.0.0.1:8000/api/v1/journals?active=true'
python scripts/health_check.py
python scripts/health_check.py --compact
python scripts/health_check.py --summary-only --compact
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

`/api/v1/system/status` 会返回 `config_warnings`，用于提示 OpenAlex、Unpaywall、LLM 等可选外部能力是否还未配置；缺失不会阻断默认离线模式。
同一响应里的 `release_readiness` 会汇总演示数据、失败工作流、配置 warning 和存储可写性，阻断原因分别放在 `demo_data_missing`、`failed_workflows`、`config_warning_codes` 和 `storage_errors`；`python scripts/health_check.py --summary-only --compact` 与 `--require-release-ready` 都会优先使用这个 API 聚合结果输出或阻断发布就绪状态。compact summary 会额外给出 `workflows_ok`、`config_ready` 和 `release_blockers`，便于快速判断是任务失败、配置未完成还是存储/演示数据阻断。
同一响应里的 `translation_adapter` 和 `llm_model` 会说明当前翻译链路使用本地 `local-echo` 还是 `openai-compatible`，`python scripts/health_check.py` 会把这两个字段作为发布健康契约校验。

导出 OpenAPI JSON 给前端、评审或发布流程使用时，不启动服务也可以生成当前接口 schema：

```bash
python scripts/export_openapi.py --output out/openapi.json
python scripts/export_release_artifacts.py --output-dir out/release --compact
python scripts/validate_release_artifacts.py --artifact-dir out/release --compact
python scripts/package_release_artifacts.py --artifact-dir out/release --output out/paper-lab-agent-release.zip --compact
python scripts/validate_release_package.py --package out/paper-lab-agent-release.zip --compact
```

`scripts/export_release_artifacts.py` 会一次性生成 `openapi.json`、`demo-summary.json` 和 `release-manifest.json`，用于前后端、评审或发布交接。manifest 会记录来源 git commit/branch、导出时 worktree 是否 dirty，以及三个文件的 SHA256 校验和；`scripts/validate_release_artifacts.py` 会校验交接包文件是否齐全、校验和是否匹配、版本是否一致、演示摘要是否 ready，以及 OpenAPI 是否包含基础路径。`scripts/package_release_artifacts.py` 会先校验目录，再打包为单个 zip 并输出包的 SHA256；`scripts/validate_release_package.py` 会解压并复验 zip 内 artifacts，防止交接文件被篡改或缺项。正式交接前可追加 `--require-clean-source`，要求 manifest 里的 `source.git_dirty=false`。服务启动后也可以直接访问 live schema 与交互文档：`http://127.0.0.1:8000/openapi.json`、`http://127.0.0.1:8000/docs` 和 `http://127.0.0.1:8000/redoc`。`python scripts/health_check.py --check-openapi` 会探测 live `/openapi.json` 并校验基础 schema 契约；`--require-openapi` 会在 schema 不可访问或缺少必需路径、tag、错误响应模型时返回非零。

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

默认关闭 scheduler，避免本地离线测试和首次启动时自动访问外部 API。启用后可在 Streamlit 侧边栏或 `/api/v1/system/status` 的 `runtime.scheduler_enabled` 确认状态；`runtime.scheduler_jobs` 会列出 daily / weekly / monthly 抓取计划和 UTC 触发时间。

## Backend Only

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Streamlit

```bash
python -m streamlit run streamlit_app.py
```

默认前端连接 `http://127.0.0.1:8000/api/v1`。如需修改：

```bash
API_BASE_URL=http://127.0.0.1:8000/api/v1 python -m streamlit run streamlit_app.py
```

## Optional GROBID

GROBID 只在解析真实 PDF 时需要。离线测试和本地文本 fallback 不依赖它。
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

这两条命令会执行与 CI 相同的离线发布检查：先用 strict doctor 阻断缺失依赖或关键文件，再校验启动脚本语法、编译关键脚本、运行全量测试。
发布或演示前的完整检查顺序见 [docs/release-checklist.md](docs/release-checklist.md)。

`python scripts/health_check.py --check-frontend` 会额外探测 Streamlit `/_stcore/health`，用于确认 `scripts/dev.sh` 启动后的后端和前端都可访问。
`python scripts/health_check.py --summary-only --compact` 会输出短摘要，包含 `release_ready`、`release_blockers`、`api_status`、`demo_data_ready`、`failed_workflows`、`workflows_ok`、`config_warning_count`、`config_ready`、`config_warning_codes`、`storage_writable` 和 `storage_errors`，适合发布或演示前快速确认 live 环境；搭配 `--check-frontend` 时还会返回 `frontend_ok`、`frontend_status_code` 和 `frontend_url`，搭配 `--check-openapi` 时还会返回 `openapi_ok`、`openapi_path_count` 和 `openapi_tag_names`，搭配 `--check-external` 时还会返回 `grobid_available`、`grobid_status_code`、`grobid_url` 和 `grobid_error`。如果这些显式探测失败，`release_blockers` 也会追加 `frontend:*`、`openapi:*` 或 `grobid:*` 阻断项。
`python scripts/health_check.py --require-frontend` 会主动探测 Streamlit，并在前端健康探针不是 200 时返回非零，适合 `scripts/dev.sh` 启动后做发布或演示前门禁。
`python scripts/health_check.py --require-openapi` 会主动探测 live `/openapi.json`，并在 OpenAPI schema 不可访问或基础契约不完整时返回非零，适合接口交付或前端联调前门禁。
`python scripts/health_check.py --require-storage-writable` 会在数据目录、PDF/TEI/翻译/导出目录、数据库父目录或向量索引父目录不可写，或已存在的本地向量索引 JSON 损坏时返回非零，适合发布前预检本机运行环境。
`python scripts/health_check.py --require-no-failed-workflows` 会在抓取、解析、索引、翻译、化学抽取或反应集复核状态统计中存在 failed 项时返回非零，适合部署前确认没有已知失败积压。
`python scripts/health_check.py --require-no-config-warnings` 会在 OpenAlex、Unpaywall、LLM、向量后端等配置告警存在时返回非零，适合正式演示或部署前确认外部能力已按预期配置。
`python scripts/health_check.py --require-demo-data` 会在 live API 的 `counts` 缺少期刊、论文、文档、章节、chunk、反应集或反应样例时返回非零，适合正式演示前确认 walking skeleton 数据已准备好。
`python scripts/health_check.py --require-release-ready` 会组合 storage writable、no failed workflows、no config warnings 和 demo data 四个门禁，适合发布或正式演示前一条命令预检；前端和 GROBID 仍用 `--require-frontend`、`--require-grobid` 按需单独强制。
`DEV_EXIT_AFTER_READY=true bash scripts/dev.sh` 会在 API 和 Streamlit 都 ready 后退出并清理子进程，适合 CI 或发布前验证统一启动命令本身。

如需只跑离线 walking skeleton smoke：

```bash
python -m scripts.smoke_check
```

该 smoke 会在临时目录初始化空库、导入 fixture 论文、验证 `/papers` 检索，并跑通 PDF fallback 的上传、解析、索引、RAG 查询，以及翻译、化学抽取、复核闸门和导出，不访问外部服务。

如需只跑测试：

```bash
python -m pytest -q
```

默认测试使用临时 SQLite 数据库和本地 fixture，不依赖外部网络、GROBID 或真实模型。

CI 配置在 `.github/workflows/ci.yml`，默认跑同一条离线测试命令；GitHub Actions 也支持 `workflow_dispatch`，可在发布或演示前手动触发 release gate。

## Troubleshooting

- API 端口冲突：`API_PORT=8001 bash scripts/dev.sh`
- Streamlit 端口冲突：`STREAMLIT_PORT=8502 bash scripts/dev.sh`
- 慢机器启动超时：`DEV_READY_TIMEOUT=60 bash scripts/dev.sh`
- 指定解释器：`PYTHON=.venv/bin/python bash scripts/dev.sh`
- GROBID 未启动：解析会降级为本地文本 fallback，`documents.parse_error` 会记录原因。
- 外部 API 未配置：OpenAlex、Unpaywall、LLM 均从 `.env` 读取；未配置时系统保持本地可运行，不用假数据冒充外部能力。

## Productization Roadmap

成品化阶段见 [docs/productization-roadmap.md](docs/productization-roadmap.md)。
