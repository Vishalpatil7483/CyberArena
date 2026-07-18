"""Lab and progress business logic."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.lab import Lab, ProgressStatus, UserLabProgress


class LabNotFoundError(Exception):
    """Raised when a slug does not match an active lab."""


@dataclass(frozen=True)
class LabStats:
    """Aggregate lab statistics for a user's dashboard."""

    total_labs: int
    completed: int
    in_progress: int

    @property
    def completion_percent(self) -> int:
        if self.total_labs == 0:
            return 0
        return round(self.completed * 100 / self.total_labs)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def list_active_labs(db: Session) -> list[Lab]:
    """Return all active labs ordered by category, then title."""
    return list(
        db.scalars(
            select(Lab)
            .where(Lab.is_active.is_(True))
            .order_by(Lab.category, Lab.title)
        )
    )


def get_lab_by_slug(db: Session, slug: str) -> Lab:
    """Return an active lab by slug or raise LabNotFoundError."""
    lab = db.scalar(
        select(Lab).where(Lab.slug == slug, Lab.is_active.is_(True))
    )
    if lab is None:
        raise LabNotFoundError()
    return lab


def get_progress(
    db: Session, user_id: uuid.UUID, lab_id: uuid.UUID
) -> UserLabProgress | None:
    """Return the user's progress record for a lab, if any."""
    return db.scalar(
        select(UserLabProgress).where(
            UserLabProgress.user_id == user_id,
            UserLabProgress.lab_id == lab_id,
        )
    )


def get_progress_by_lab(
    db: Session, user_id: uuid.UUID
) -> dict[uuid.UUID, UserLabProgress]:
    """Return the user's progress records keyed by lab id (one query)."""
    records = db.scalars(
        select(UserLabProgress).where(UserLabProgress.user_id == user_id)
    )
    return {record.lab_id: record for record in records}


def start_lab(db: Session, user_id: uuid.UUID, lab: Lab) -> UserLabProgress:
    """Create an in-progress record for the lab, or return the existing one.

    Idempotent: starting an already started or completed lab never creates
    a duplicate and never regresses status (guarded by a unique constraint
    against concurrent requests).
    """
    existing = get_progress(db, user_id, lab.id)
    if existing is not None:
        return existing

    progress = UserLabProgress(
        user_id=user_id,
        lab_id=lab.id,
        status=ProgressStatus.IN_PROGRESS,
        started_at=_utcnow(),
    )
    db.add(progress)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race with a concurrent start; return the winner's record.
        db.rollback()
        existing = get_progress(db, user_id, lab.id)
        if existing is None:  # pragma: no cover - defensive
            raise
        return existing
    db.refresh(progress)
    return progress


def complete_lab(db: Session, user_id: uuid.UUID, lab: Lab) -> UserLabProgress:
    """Mark a lab completed for the user.

    Starts the lab implicitly if it was never started. Completing an
    already-completed lab is a no-op.
    """
    progress = start_lab(db, user_id, lab)
    if progress.status != ProgressStatus.COMPLETED:
        progress.status = ProgressStatus.COMPLETED
        progress.completed_at = _utcnow()
        db.commit()
        db.refresh(progress)
    return progress


def get_lab_stats(db: Session, user_id: uuid.UUID) -> LabStats:
    """Compute dashboard statistics with aggregate queries."""
    total_labs = db.scalar(
        select(func.count()).select_from(Lab).where(Lab.is_active.is_(True))
    )
    counts = dict(
        db.execute(
            select(UserLabProgress.status, func.count())
            .join(Lab, Lab.id == UserLabProgress.lab_id)
            .where(
                UserLabProgress.user_id == user_id,
                Lab.is_active.is_(True),
            )
            .group_by(UserLabProgress.status)
        ).all()
    )
    return LabStats(
        total_labs=total_labs or 0,
        completed=counts.get(ProgressStatus.COMPLETED, 0),
        in_progress=counts.get(ProgressStatus.IN_PROGRESS, 0),
    )
