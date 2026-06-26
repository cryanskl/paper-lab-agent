from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from app import __version__
from app.config import get_settings
from app.db import init_db
from app.errors import install_error_handlers, install_openapi_error_schema
from app.routers import categories, crawl, documents, journals, papers, rag, reactions, system
from app.scheduler import create_scheduler


class HealthResponse(BaseModel):
    status: str
    service: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    settings = get_settings()
    scheduler = create_scheduler() if settings.scheduler_enabled else None
    if scheduler is not None:
        scheduler.start()
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="paper-lab-agent", version=__version__, lifespan=lifespan)
    install_error_handlers(app)

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> dict:
        return {"status": "ok", "service": "paper-lab-agent"}

    @app.get(f"{settings.api_prefix}/health", response_model=HealthResponse, tags=["system"])
    def api_health() -> dict:
        return {"status": "ok", "service": "paper-lab-agent"}

    app.include_router(journals.router, prefix=settings.api_prefix)
    app.include_router(categories.router, prefix=settings.api_prefix)
    app.include_router(crawl.router, prefix=settings.api_prefix)
    app.include_router(papers.router, prefix=settings.api_prefix)
    app.include_router(documents.router, prefix=settings.api_prefix)
    app.include_router(rag.router, prefix=settings.api_prefix)
    app.include_router(reactions.router, prefix=settings.api_prefix)
    app.include_router(system.router, prefix=settings.api_prefix)
    install_openapi_error_schema(app)

    return app


app = create_app()
