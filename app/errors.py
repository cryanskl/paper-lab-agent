from typing import Any, Literal, Optional

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


logger = logging.getLogger(__name__)


def error_response(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


class AppError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, extra: Optional[dict] = None):
        detail = error_response(code, message)
        if extra:
            detail.update(extra)
        super().__init__(status_code=status_code, detail=detail)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PageResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class AsyncJobResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    job_id: int
    status: Literal["pending"]


class AsyncJobsResponse(BaseModel):
    jobs: list[AsyncJobResponse]


def install_openapi_error_schema(app: FastAPI) -> None:
    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, tags=app.openapi_tags, routes=app.routes)
        schemas = schema.setdefault("components", {}).setdefault("schemas", {})
        schemas["ErrorDetail"] = {
            "type": "object",
            "required": ["code", "message"],
            "properties": {
                "code": {"type": "string", "title": "Code"},
                "message": {"type": "string", "title": "Message"},
            },
            "title": "ErrorDetail",
        }
        schemas["ErrorResponse"] = {
            "type": "object",
            "required": ["error"],
            "properties": {"error": {"$ref": "#/components/schemas/ErrorDetail"}},
            "title": "ErrorResponse",
        }
        for path, methods in schema.get("paths", {}).items():
            if not str(path).startswith("/api/v1"):
                continue
            for operation in methods.values():
                responses = operation.get("responses", {})
                for status_code, response in list(responses.items()):
                    if not str(status_code).isdigit() or int(status_code) < 400:
                        continue
                    responses[status_code] = {
                        "description": response.get("description") or "Error response",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                            }
                        },
                    }
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi


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
