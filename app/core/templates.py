"""Shared Jinja2 templates instance."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.config import get_settings

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_settings = get_settings()
templates.env.globals["app_name"] = _settings.app_name
templates.env.globals["app_version"] = _settings.app_version
