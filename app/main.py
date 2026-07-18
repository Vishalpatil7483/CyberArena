"""Application factory and ASGI entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth.routes import router as auth_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import SecurityHeadersMiddleware
from app.core.routes import router as pages_router
from app.dashboard.routes import router as dashboard_router
from app.labs.routes import router as labs_router

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = get_logger(__name__)
    settings = get_settings()
    logger.info(
        "Starting %s v%s (%s)",
        settings.app_name,
        settings.app_version,
        settings.environment.value,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie=settings.session_cookie_name,
        max_age=settings.session_max_age,
        same_site="lax",
        https_only=settings.is_production,
    )
    register_exception_handlers(app)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(pages_router)
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(labs_router)

    return app


app = create_app()
