# paper-lab-agent

低温等离子体文献检索与理解系统。V1 采用 local-first 架构：FastAPI + SQLite + APScheduler + GROBID + Chroma/FAISS 兼容的本地索引约定，前端使用 Streamlit。

当前版本：`0.1.0`

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
bash scripts/dev.sh
```

服务启动时会自动用 `docs/schema.sql` 初始化 `data/plasma.db`。
`scripts/dev.sh` 会等待 FastAPI `/api/v1/health` 和 Streamlit `/_stcore/health` 都可访问后再打印地址。

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
python scripts/health_check.py --check-frontend
python scripts/health_check.py --check-frontend --frontend-url http://127.0.0.1:8501
API_BASE_URL=http://127.0.0.1:8001/api/v1 python scripts/health_check.py
```

`/api/v1/system/status` 会返回 `config_warnings`，用于提示 OpenAlex、Unpaywall、LLM 等可选外部能力是否还未配置；缺失不会阻断默认离线模式。
同一响应里的 `translation_adapter` 和 `llm_model` 会说明当前翻译链路使用本地 `local-echo` 还是 `openai-compatible`，`python scripts/health_check.py` 会把这两个字段作为发布健康契约校验。

导入离线样例论文和 PDF 文档：

```bash
python scripts/import_fixtures.py
python scripts/prepare_demo_data.py
python scripts/prepare_demo_data.py --compact
python scripts/prepare_demo_data.py --summary-only --compact
python scripts/health_check.py --require-demo-data
curl 'http://127.0.0.1:8000/api/v1/papers?q=plasma'
curl 'http://127.0.0.1:8000/api/v1/documents'
```

`scripts/import_fixtures.py` 只导入论文和 PDF fixture；`scripts/prepare_demo_data.py` 会继续跑解析、索引、翻译、化学抽取、人工复核标记和三种导出，适合正式演示前一次性准备 walking skeleton 数据。`--compact` 会输出单行完整 JSON，可看 `summary.ready`；`--summary-only --compact` 只输出发布摘要，可直接看顶层 `ready`、`export_formats` 和核心状态字段。

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
bash scripts/release_check.sh
```

这条命令会执行与 CI 相同的离线发布检查：校验启动脚本语法、编译关键脚本、运行全量测试。

`python scripts/health_check.py --check-frontend` 会额外探测 Streamlit `/_stcore/health`，用于确认 `scripts/dev.sh` 启动后的后端和前端都可访问。
`python scripts/health_check.py --summary-only --compact` 会输出短摘要，包含 `api_status`、`demo_data_ready`、`failed_workflows`、`config_warning_count` 和 `storage_writable`，适合发布或演示前快速确认 live 环境；搭配 `--check-frontend` 时还会返回 `frontend_ok`、`frontend_status_code` 和 `frontend_url`，搭配 `--check-external` 时还会返回 `grobid_available`、`grobid_status_code`、`grobid_url` 和 `grobid_error`。
`python scripts/health_check.py --require-storage-writable` 会在数据目录、PDF/TEI/翻译/导出目录、数据库父目录或向量索引父目录不可写时返回非零，适合发布前预检本机运行环境。
`python scripts/health_check.py --require-no-failed-workflows` 会在抓取、解析、索引、翻译、化学抽取或反应集复核状态统计中存在 failed 项时返回非零，适合部署前确认没有已知失败积压。
`python scripts/health_check.py --require-no-config-warnings` 会在 OpenAlex、Unpaywall、LLM、向量后端等配置告警存在时返回非零，适合正式演示或部署前确认外部能力已按预期配置。
`python scripts/health_check.py --require-demo-data` 会在 live API 的 `counts` 缺少期刊、论文、文档、章节、chunk、反应集或反应样例时返回非零，适合正式演示前确认 walking skeleton 数据已准备好。

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

CI 配置在 `.github/workflows/ci.yml`，默认跑同一条离线测试命令。

## Troubleshooting

- API 端口冲突：`API_PORT=8001 bash scripts/dev.sh`
- Streamlit 端口冲突：`STREAMLIT_PORT=8502 bash scripts/dev.sh`
- 慢机器启动超时：`DEV_READY_TIMEOUT=60 bash scripts/dev.sh`
- 指定解释器：`PYTHON=.venv/bin/python bash scripts/dev.sh`
- GROBID 未启动：解析会降级为本地文本 fallback，`documents.parse_error` 会记录原因。
- 外部 API 未配置：OpenAlex、Unpaywall、LLM 均从 `.env` 读取；未配置时系统保持本地可运行，不用假数据冒充外部能力。

## Productization Roadmap

成品化阶段见 [docs/productization-roadmap.md](docs/productization-roadmap.md)。
