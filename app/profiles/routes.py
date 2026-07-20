"""Profile and leaderboard routes. Thin: logic lives in services."""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_login
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.core.templates import templates
from app.models.user import User
from app.services import achievements as achievement_service
from app.services import profiles as profile_service

router = APIRouter(tags=["profiles"])


@router.get("/profile", include_in_schema=False)
async def my_profile(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
) -> Response:
    return templates.TemplateResponse(
        request,
        "pages/profile.html",
        {
            "user": user,
            "stats": profile_service.get_profile_stats(db, user),
            "achievements": achievement_service.get_user_achievements(db, user.id),
            "recent_activity": profile_service.get_recent_activity(db, user.id),
        },
    )


@router.get("/users/{username}", include_in_schema=False)
async def public_profile(
    request: Request,
    username: str,
    db: Session = Depends(get_db),
) -> Response:
    try:
        user = profile_service.get_user_by_username(db, username)
    except profile_service.UserNotFoundError:
        raise NotFoundError("User not found.") from None
    return templates.TemplateResponse(
        request,
        "pages/public_profile.html",
        {
            "profile_user": user,
            "stats": profile_service.get_profile_stats(db, user),
            "achievements": achievement_service.get_user_achievements(db, user.id),
        },
    )


@router.get("/leaderboard", include_in_schema=False)
async def leaderboard(
    request: Request,
    page: int = Query(1, ge=1),
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    board = profile_service.get_leaderboard(db, page)
    return templates.TemplateResponse(
        request,
        "pages/leaderboard.html",
        {
            "board": board,
            "current_username": user.username if user else None,
        },
    )
