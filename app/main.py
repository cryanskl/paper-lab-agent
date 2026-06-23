from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db import init_db
from app.errors import install_error_handlers
from app.routers import categories, crawl, documents, journals, papers, rag, reactions


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="paper-lab-agent", version="0.1.0", lifespan=lifespan)
    install_error_handlers(app)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "paper-lab-agent"}

    @app.get(f"{settings.api_prefix}/health")
    def api_health() -> dict:
        return {"status": "ok", "service": "paper-lab-agent"}

    app.include_router(journals.router, prefix=settings.api_prefix)
    app.include_router(categories.router, prefix=settings.api_prefix)
    app.include_router(crawl.router, prefix=settings.api_prefix)
    app.include_router(papers.router, prefix=settings.api_prefix)
    app.include_router(documents.router, prefix=settings.api_prefix)
    app.include_router(rag.router, prefix=settings.api_prefix)
    app.include_router(reactions.router, prefix=settings.api_prefix)

    return app


app = create_app()
