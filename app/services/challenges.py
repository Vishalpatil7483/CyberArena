"""Challenge business logic: listing, flag submission, points, completion."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import verify_flag
from app.models.challenge import Challenge, UserChallengeProgress
from app.models.lab import Lab
from app.services import labs as lab_service


class ChallengeNotFoundError(Exception):
    """Raised when a challenge id does not exist in the given lab."""


@dataclass(frozen=True)
class SubmissionResult:
    """Outcome of a flag submission."""

    correct: bool
    already_completed: bool
    points_awarded: int
    lab_completed: bool


@dataclass(frozen=True)
class ChallengeStats:
    """Aggregate challenge statistics for a user's dashboard."""

    total_challenges: int
    completed: int
    points_earned: int


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def list_challenges(db: Session, lab: Lab) -> list[Challenge]:
    """Return the lab's active challenges in display order."""
    return list(
        db.scalars(
            select(Challenge)
            .where(Challenge.lab_id == lab.id, Challenge.is_active.is_(True))
            .order_by(Challenge.order_index, Challenge.title)
        )
    )


def get_challenge(db: Session, lab: Lab, challenge_id: uuid.UUID) -> Challenge:
    """Return an active challenge belonging to the lab, or raise."""
    challenge = db.scalar(
        select(Challenge).where(
            Challenge.id == challenge_id,
            Challenge.lab_id == lab.id,
            Challenge.is_active.is_(True),
        )
    )
    if challenge is None:
        raise ChallengeNotFoundError()
    return challenge


def get_challenge_progress(
    db: Session, user_id: uuid.UUID, challenge_id: uuid.UUID
) -> UserChallengeProgress | None:
    """Return the user's progress record for a challenge, if any."""
    return db.scalar(
        select(UserChallengeProgress).where(
            UserChallengeProgress.user_id == user_id,
            UserChallengeProgress.challenge_id == challenge_id,
        )
    )


def get_progress_by_challenge(
    db: Session, user_id: uuid.UUID, lab: Lab
) -> dict[uuid.UUID, UserChallengeProgress]:
    """Return the user's progress for a lab's challenges keyed by id."""
    records = db.scalars(
        select(UserChallengeProgress)
        .join(Challenge, Challenge.id == UserChallengeProgress.challenge_id)
        .where(
            UserChallengeProgress.user_id == user_id,
            Challenge.lab_id == lab.id,
        )
    )
    return {record.challenge_id: record for record in records}


def _get_or_create_progress(
    db: Session, user_id: uuid.UUID, challenge_id: uuid.UUID
) -> UserChallengeProgress:
    """Fetch the progress record, creating it if missing (race-safe)."""
    progress = get_challenge_progress(db, user_id, challenge_id)
    if progress is not None:
        return progress

    progress = UserChallengeProgress(user_id=user_id, challenge_id=challenge_id)
    db.add(progress)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race with a concurrent submission; use the winner's record.
        db.rollback()
        progress = get_challenge_progress(db, user_id, challenge_id)
        if progress is None:  # pragma: no cover - defensive
            raise
    else:
        db.refresh(progress)
    return progress


def calculate_lab_completion(
    db: Session, user_id: uuid.UUID, lab: Lab
) -> tuple[int, int]:
    """Return (completed, total) active-challenge counts for the user."""
    total = db.scalar(
        select(func.count())
        .select_from(Challenge)
        .where(Challenge.lab_id == lab.id, Challenge.is_active.is_(True))
    )
    completed = db.scalar(
        select(func.count())
        .select_from(UserChallengeProgress)
        .join(Challenge, Challenge.id == UserChallengeProgress.challenge_id)
        .where(
            UserChallengeProgress.user_id == user_id,
            UserChallengeProgress.is_completed.is_(True),
            Challenge.lab_id == lab.id,
            Challenge.is_active.is_(True),
        )
    )
    return completed or 0, total or 0


def submit_flag(
    db: Session,
    user_id: uuid.UUID,
    lab: Lab,
    challenge: Challenge,
    submitted_flag: str,
) -> SubmissionResult:
    """Process a flag submission.

    Ensures the lab is started, increments attempts on wrong answers,
    awards points exactly once, and auto-completes the lab when its last
    challenge is solved.
    """
    lab_service.start_lab(db, user_id, lab)
    progress = _get_or_create_progress(db, user_id, challenge.id)

    if progress.is_completed:
        return SubmissionResult(
            correct=True,
            already_completed=True,
            points_awarded=0,
            lab_completed=False,
        )

    progress.attempts += 1
    if not verify_flag(submitted_flag, challenge.flag_hash):
        db.commit()
        return SubmissionResult(
            correct=False,
            already_completed=False,
            points_awarded=0,
            lab_completed=False,
        )

    progress.is_completed = True
    progress.completed_at = _utcnow()
    db.commit()

    completed, total = calculate_lab_completion(db, user_id, lab)
    lab_completed = total > 0 and completed == total
    if lab_completed:
        lab_service.complete_lab(db, user_id, lab)

    return SubmissionResult(
        correct=True,
        already_completed=False,
        points_awarded=challenge.points,
        lab_completed=lab_completed,
    )


def get_challenge_stats(db: Session, user_id: uuid.UUID) -> ChallengeStats:
    """Compute dashboard challenge statistics with aggregate queries."""
    total = db.scalar(
        select(func.count())
        .select_from(Challenge)
        .join(Lab, Lab.id == Challenge.lab_id)
        .where(Challenge.is_active.is_(True), Lab.is_active.is_(True))
    )
    completed, points = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(Challenge.points), 0),
        )
        .select_from(UserChallengeProgress)
        .join(Challenge, Challenge.id == UserChallengeProgress.challenge_id)
        .join(Lab, Lab.id == Challenge.lab_id)
        .where(
            UserChallengeProgress.user_id == user_id,
            UserChallengeProgress.is_completed.is_(True),
            Challenge.is_active.is_(True),
            Lab.is_active.is_(True),
        )
    ).one()
    return ChallengeStats(
        total_challenges=total or 0,
        completed=completed or 0,
        points_earned=points or 0,
    )
