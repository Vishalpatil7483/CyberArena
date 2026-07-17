"""Public pages: landing page and health check."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.services.health import get_health_status

router = APIRouter(tags=["pages"])


@router.get("/", include_in_schema=False)
async def index(request: Request):
    return templates.TemplateResponse(request, "pages/index.html")


@router.get("/health")
async def health(db: Session = Depends(get_db)) -> dict:
    return get_health_status(db)
