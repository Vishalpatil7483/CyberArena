"""Authentication dependencies for protecting routes."""

import uuid

from fastapi import Depends, Request, status
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from app.auth.services import get_user_by_id
from app.core.database import get_db
from app.core.security import SESSION_USER_KEY
from app.models.user import User


class LoginRequiredError(HTTPException):
    """Raised when an unauthenticated request hits a protected route."""

    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required.")


def login_user(request: Request, user: User) -> None:
    """Store the user's id in the session (rotating the session content)."""
    request.session.clear()
    request.session[SESSION_USER_KEY] = str(user.id)


def logout_user(request: Request) -> None:
    """Destroy the session."""
    request.session.clear()


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
    """Return the logged-in user, or None for anonymous requests."""
    raw_id = request.session.get(SESSION_USER_KEY)
    if not raw_id:
        return None
    try:
        user_id = uuid.UUID(raw_id)
    except ValueError:
        request.session.clear()
        return None
    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        request.session.clear()
        return None
    return user


def require_login(user: User | None = Depends(get_current_user)) -> User:
    """Dependency for protected routes; raises if not authenticated."""
    if user is None:
        raise LoginRequiredError()
    return user
