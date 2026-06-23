from fastapi import FastAPI

from app.config import get_settings
from app.db import init_db
from app.errors import install_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="paper-lab-agent", version="0.1.0")
    install_error_handlers(app)

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "paper-lab-agent"}

    @app.get(f"{settings.api_prefix}/health")
    def api_health() -> dict:
        return {"status": "ok", "service": "paper-lab-agent"}

    return app


app = create_app()

