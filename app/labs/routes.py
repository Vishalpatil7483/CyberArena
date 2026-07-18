"""Lab browsing and progress routes. Thin: logic lives in services.labs."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_login
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.core.security import get_csrf_token, validate_csrf_token
from app.core.templates import templates
from app.models.lab import Lab
from app.models.user import User
from app.services import labs as lab_service

router = APIRouter(prefix="/labs", tags=["labs"])


def _get_lab_or_404(db: Session, slug: str) -> Lab:
    try:
        return lab_service.get_lab_by_slug(db, slug)
    except lab_service.LabNotFoundError:
        raise NotFoundError("Lab not found.") from None


def _progress_map(
    db: Session, user: User | None
) -> dict[uuid.UUID, object]:
    return lab_service.get_progress_by_lab(db, user.id) if user else {}


@router.get("", include_in_schema=False)
async def lab_list(
    request: Request,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    labs = lab_service.list_active_labs(db)
    return templates.TemplateResponse(
        request,
        "pages/labs.html",
        {"labs": labs, "progress_map": _progress_map(db, user)},
    )


@router.get("/{slug}", include_in_schema=False)
async def lab_detail(
    request: Request,
    slug: str,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    lab = _get_lab_or_404(db, slug)
    progress = (
        lab_service.get_progress(db, user.id, lab.id) if user else None
    )
    return templates.TemplateResponse(
        request,
        "pages/lab_detail.html",
        {
            "lab": lab,
            "progress": progress,
            "csrf_token": get_csrf_token(request),
        },
    )


def _csrf_or_redirect(
    request: Request, csrf_token: str, slug: str
) -> RedirectResponse | None:
    """Return a redirect back to the lab if the CSRF token is invalid."""
    if not validate_csrf_token(request, csrf_token):
        return RedirectResponse(
            f"/labs/{slug}", status_code=status.HTTP_303_SEE_OTHER
        )
    return None


@router.post("/{slug}/start", include_in_schema=False)
async def lab_start(
    request: Request,
    slug: str,
    csrf_token: Annotated[str, Form()] = "",
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
) -> Response:
    lab = _get_lab_or_404(db, slug)
    redirect = _csrf_or_redirect(request, csrf_token, lab.slug)
    if redirect is None:
        lab_service.start_lab(db, user.id, lab)
        redirect = RedirectResponse(
            f"/labs/{lab.slug}", status_code=status.HTTP_303_SEE_OTHER
        )
    return redirect


@router.post("/{slug}/complete", include_in_schema=False)
async def lab_complete(
    request: Request,
    slug: str,
    csrf_token: Annotated[str, Form()] = "",
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
) -> Response:
    lab = _get_lab_or_404(db, slug)
    redirect = _csrf_or_redirect(request, csrf_token, lab.slug)
    if redirect is None:
        lab_service.complete_lab(db, user.id, lab)
        redirect = RedirectResponse(
            f"/labs/{lab.slug}", status_code=status.HTTP_303_SEE_OTHER
        )
    return redirect
