"""Health/status checks used by the landing and health endpoints."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings


def get_health_status(db: Session) -> dict:
    """Return application health information, including DB connectivity."""
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # pragma: no cover - depends on external DB state
        database = "unavailable"

    return {
        "status": "ok" if database == "ok" else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment.value,
        "database": database,
    }
