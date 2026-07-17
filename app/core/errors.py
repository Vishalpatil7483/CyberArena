"""Centralized error handling.

Domain code raises ``AppError`` subclasses; the handlers registered here
translate them (and unexpected exceptions) into JSON responses for API
routes or rendered error pages for browser requests.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.templates import templates

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for application errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An internal error occurred."

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource conflict."


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation failed."


def _wants_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept and not request.url.path.startswith("/api")


def _error_response(request: Request, status_code: int, detail: str) -> Response:
    if _wants_html(request):
        if status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(
                url=f"/login?next={request.url.path}",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        template = "errors/404.html" if status_code == 404 else "errors/error.html"
        return templates.TemplateResponse(
            request,
            template,
            {"status_code": status_code, "detail": detail},
            status_code=status_code,
        )
    return JSONResponse(status_code=status_code, content={"detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> Response:
        logger.warning("AppError on %s: %s", request.url.path, exc.detail)
        return _error_response(request, exc.status_code, exc.detail)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> Response:
        return _error_response(request, exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> Response:
        logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
        logger.exception("Unhandled error on %s", request.url.path)
        return _error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "An internal error occurred.",
        )
