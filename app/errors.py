from typing import Optional

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


def error_response(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


class AppError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, extra: Optional[dict] = None):
        detail = error_response(code, message)
        if extra:
            detail.update(extra)
        super().__init__(status_code=status_code, detail=detail)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    @app.exception_handler(HTTPException)
    async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content=error_response("http_error", str(exc.detail)))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content=error_response("validation_error", str(exc)))

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error on %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content=error_response("internal_server_error", "Internal server error"))


def page(items: list[dict], total: int, page_num: int, page_size: int) -> dict:
    return {"items": items, "total": total, "page": page_num, "page_size": page_size}
