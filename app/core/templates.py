"""Shared Jinja2 templates instance."""

from pathlib import Path

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.core.config import get_settings
from app.core.security import SESSION_USER_KEY, get_csrf_token

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _is_authenticated(request: Request) -> bool:
    """Template helper: whether the request has a logged-in session."""
    return bool(request.session.get(SESSION_USER_KEY))


_settings = get_settings()
templates.env.globals["app_name"] = _settings.app_name
templates.env.globals["app_version"] = _settings.app_version
templates.env.globals["is_authenticated"] = _is_authenticated
templates.env.globals["csrf_token_for"] = get_csrf_token
