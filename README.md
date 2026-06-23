# paper-lab-agent

低温等离子体文献检索与理解系统。V1 采用 local-first 架构：FastAPI + SQLite + APScheduler + GROBID + Chroma/FAISS 兼容的本地索引约定，前端使用 Streamlit。

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

服务启动时会自动用 `docs/schema.sql` 初始化 `data/plasma.db`。

验证：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/health
curl 'http://127.0.0.1:8000/api/v1/journals?active=true'
```

导入离线样例论文：

```bash
python scripts/import_fixtures.py
curl 'http://127.0.0.1:8000/api/v1/papers?q=plasma'
```

## Streamlit

```bash
streamlit run streamlit_app.py
```

默认前端连接 `http://127.0.0.1:8000/api/v1`。如需修改：

```bash
API_BASE_URL=http://127.0.0.1:8000/api/v1 streamlit run streamlit_app.py
```

## Verification

```bash
pytest
```

默认测试使用临时 SQLite 数据库和本地 fixture，不依赖外部网络、GROBID 或真实模型。

## Productization Roadmap

成品化阶段见 [docs/productization-roadmap.md](docs/productization-roadmap.md)。
