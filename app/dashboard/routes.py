"""Dashboard routes."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import require_login
from app.core.database import get_db
from app.core.security import get_csrf_token
from app.core.templates import templates
from app.models.user import User
from app.services import challenges as challenge_service
from app.services import labs as lab_service

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", include_in_schema=False)
async def dashboard(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
) -> Response:
    return templates.TemplateResponse(
        request,
        "pages/dashboard.html",
        {
            "user": user,
            "stats": lab_service.get_lab_stats(db, user.id),
            "challenge_stats": challenge_service.get_challenge_stats(db, user.id),
            "csrf_token": get_csrf_token(request),
        },
    )
