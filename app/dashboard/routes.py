"""Dashboard routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.auth.dependencies import require_login
from app.core.templates import templates
from app.models.user import User

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", include_in_schema=False)
async def dashboard(request: Request, user: User = Depends(require_login)) -> Response:
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {"user": user},
        headers={"Cache-Control": "no-store"},
    )
