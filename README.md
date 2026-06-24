# paper-lab-agent

低温等离子体文献检索与理解系统。V1 采用 local-first 架构：FastAPI + SQLite + APScheduler + GROBID + Chroma/FAISS 兼容的本地索引约定，前端使用 Streamlit。

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
curl 'http://127.0.0.1:8000/api/v1/journals?active=true'
python scripts/health_check.py
```

导入离线样例论文：

```bash
python scripts/import_fixtures.py
curl 'http://127.0.0.1:8000/api/v1/papers?q=plasma'
```

启用定时抓取：

```bash
PAPER_LAB_SCHEDULER_ENABLED=true bash scripts/dev.sh
```

默认关闭 scheduler，避免本地离线测试和首次启动时自动访问外部 API。启用后可在 Streamlit 侧边栏或 `/api/v1/system/status` 的 `runtime.scheduler_enabled` 确认状态。

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

```bash
docker run --rm -p 8070:8070 lfoppiano/grobid
python scripts/health_check.py --check-external
```

## Verification

```bash
bash scripts/release_check.sh
```

这条命令会执行与 CI 相同的离线发布检查：校验启动脚本语法、编译关键脚本、运行全量测试。

如需只跑离线 walking skeleton smoke：

```bash
python -m scripts.smoke_check
```

该 smoke 会在临时目录初始化空库、导入 fixture 论文、验证 `/papers` 检索，并跑通 PDF fallback 的上传、解析、索引和 RAG 查询，不访问外部服务。

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
