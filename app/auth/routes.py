"""Authentication routes. Thin: validation and logic live in services."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.auth import services
from app.auth.dependencies import (
    get_current_user,
    login_user,
    logout_user,
    require_login,
)
from app.core.database import get_db
from app.core.security import get_csrf_token, validate_csrf_token
from app.core.templates import templates
from app.models.user import User

router = APIRouter(tags=["auth"])


def _safe_next_url(next_url: str | None) -> str:
    """Allow only same-site relative redirect targets.

    Rejects scheme-relative (//host) and backslash variants (/\\host) that
    some browsers normalize into cross-origin redirects.
    """
    if (
        next_url
        and next_url.startswith("/")
        and not next_url.startswith("//")
        and "\\" not in next_url
    ):
        return next_url
    return "/dashboard"


def _render_register(
    request: Request,
    errors: list[str] | None = None,
    form: dict[str, str] | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    return templates.TemplateResponse(
        request,
        "pages/register.html",
        {
            "errors": errors or [],
            "form": form or {},
            "csrf_token": get_csrf_token(request),
        },
        status_code=status_code,
    )


def _render_login(
    request: Request,
    errors: list[str] | None = None,
    form: dict[str, str] | None = None,
    status_code: int = status.HTTP_200_OK,
    message: str | None = None,
) -> Response:
    return templates.TemplateResponse(
        request,
        "pages/login.html",
        {
            "errors": errors or [],
            "form": form or {},
            "message": message,
            "csrf_token": get_csrf_token(request),
        },
        status_code=status_code,
    )


@router.get("/register", include_in_schema=False)
async def register_page(
    request: Request, user: User | None = Depends(get_current_user)
) -> Response:
    if user is not None:
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return _render_register(request)


@router.post("/register", include_in_schema=False)
async def register_submit(
    request: Request,
    username: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    password_confirm: Annotated[str, Form()] = "",
    csrf_token: Annotated[str, Form()] = "",
    db: Session = Depends(get_db),
) -> Response:
    username = username.strip()
    email = email.strip()
    form = {"username": username, "email": email}

    if not validate_csrf_token(request, csrf_token):
        return _render_register(
            request,
            errors=["Your session expired. Please try again."],
            form=form,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    errors = services.validate_registration(username, email, password, password_confirm)
    if not errors:
        if services.username_taken(db, username):
            errors.append("That username is already taken.")
        if services.email_taken(db, email):
            errors.append("That email address is already registered.")
    if errors:
        return _render_register(
            request, errors=errors, form=form, status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        services.register_user(db, username, email, password)
    except services.DuplicateUserError:
        # Lost a race with a concurrent registration for the same name/email.
        return _render_register(
            request,
            errors=["That username or email is already registered."],
            form=form,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return RedirectResponse(
        "/login?registered=1", status_code=status.HTTP_303_SEE_OTHER
    )


@router.get("/login", include_in_schema=False)
async def login_page(
    request: Request,
    registered: Annotated[str | None, Query()] = None,
    user: User | None = Depends(get_current_user),
) -> Response:
    if user is not None:
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    message = "Account created. Please sign in." if registered else None
    return _render_login(request, message=message)


@router.post("/login", include_in_schema=False)
async def login_submit(
    request: Request,
    identifier: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    csrf_token: Annotated[str, Form()] = "",
    next_url: Annotated[str | None, Query(alias="next")] = None,
    db: Session = Depends(get_db),
) -> Response:
    identifier = identifier.strip()
    form = {"identifier": identifier}

    if not validate_csrf_token(request, csrf_token):
        return _render_login(
            request,
            errors=["Your session expired. Please try again."],
            form=form,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = services.authenticate_user(db, identifier, password)
    if user is None:
        return _render_login(
            request,
            errors=["Invalid credentials."],
            form=form,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    login_user(request, user)
    return RedirectResponse(
        _safe_next_url(next_url), status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/logout", include_in_schema=False)
async def logout(
    request: Request,
    csrf_token: Annotated[str, Form()] = "",
    user: User = Depends(require_login),
) -> Response:
    if not validate_csrf_token(request, csrf_token):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    logout_user(request)
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
