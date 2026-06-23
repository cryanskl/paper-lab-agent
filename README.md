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
```

## Streamlit

```bash
streamlit run streamlit_app.py
```

