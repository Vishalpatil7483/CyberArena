"""Profile and leaderboard business logic."""

import math
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from app.models.challenge import Challenge, UserChallengeProgress
from app.models.lab import Lab, ProgressStatus, UserLabProgress
from app.models.user import User

LEADERBOARD_PAGE_SIZE = 25


class UserNotFoundError(Exception):
    """Raised when a username does not match an active user."""


@dataclass(frozen=True)
class LeaderboardEntry:
    """One ranked row of the leaderboard."""

    rank: int
    username: str
    points: int
    completed_challenges: int
    completed_labs: int
    member_since: datetime


@dataclass(frozen=True)
class LeaderboardPage:
    """A page of leaderboard entries plus pagination metadata."""

    entries: list[LeaderboardEntry]
    page: int
    total_pages: int
    total_users: int


@dataclass(frozen=True)
class ProfileStats:
    """Aggregate statistics for a user's profile."""

    points: int
    rank: int
    completed_labs: int
    completed_challenges: int
    total_attempts: int

    @property
    def success_rate(self) -> int:
        """Solved challenges as a percentage of total attempts."""
        if self.total_attempts == 0:
            return 0
        return round(self.completed_challenges * 100 / self.total_attempts)


@dataclass(frozen=True)
class ActivityItem:
    """A recently completed challenge for the activity feed."""

    challenge_title: str
    lab_title: str
    lab_slug: str
    points: int
    completed_at: datetime


def _points_expr() -> Select:
    """Subquery: per-user earned points from completed active challenges."""
    return (
        select(
            UserChallengeProgress.user_id.label("user_id"),
            func.coalesce(func.sum(Challenge.points), 0).label("points"),
            func.count().label("completed_challenges"),
        )
        .join(Challenge, Challenge.id == UserChallengeProgress.challenge_id)
        .join(Lab, Lab.id == Challenge.lab_id)
        .where(
            UserChallengeProgress.is_completed.is_(True),
            Challenge.is_active.is_(True),
            Lab.is_active.is_(True),
        )
        .group_by(UserChallengeProgress.user_id)
        .subquery()
    )


def _labs_expr() -> Select:
    """Subquery: per-user count of completed active labs."""
    return (
        select(
            UserLabProgress.user_id.label("user_id"),
            func.count().label("completed_labs"),
        )
        .join(Lab, Lab.id == UserLabProgress.lab_id)
        .where(
            UserLabProgress.status == ProgressStatus.COMPLETED,
            Lab.is_active.is_(True),
        )
        .group_by(UserLabProgress.user_id)
        .subquery()
    )


def _ranked_users_query() -> Select:
    """Select active users with points/challenge/lab counts, ranked.

    Ordering: points desc, completed challenges desc, older account first.
    """
    points = _points_expr()
    labs = _labs_expr()
    return (
        select(
            User.username,
            User.created_at,
            func.coalesce(points.c.points, 0).label("points"),
            func.coalesce(points.c.completed_challenges, 0).label(
                "completed_challenges"
            ),
            func.coalesce(labs.c.completed_labs, 0).label("completed_labs"),
        )
        .outerjoin(points, points.c.user_id == User.id)
        .outerjoin(labs, labs.c.user_id == User.id)
        .where(User.is_active.is_(True))
        .order_by(
            func.coalesce(points.c.points, 0).desc(),
            func.coalesce(points.c.completed_challenges, 0).desc(),
            User.created_at.asc(),
        )
    )


def get_leaderboard(db: Session, page: int = 1) -> LeaderboardPage:
    """Return one page of the global leaderboard (25 rows per page)."""
    total_users = (
        db.scalar(
            select(func.count()).select_from(User).where(User.is_active.is_(True))
        )
        or 0
    )
    total_pages = max(1, math.ceil(total_users / LEADERBOARD_PAGE_SIZE))
    page = min(max(1, page), total_pages)

    rows = db.execute(
        _ranked_users_query()
        .limit(LEADERBOARD_PAGE_SIZE)
        .offset((page - 1) * LEADERBOARD_PAGE_SIZE)
    ).all()

    offset = (page - 1) * LEADERBOARD_PAGE_SIZE
    entries = [
        LeaderboardEntry(
            rank=offset + index + 1,
            username=row.username,
            points=row.points,
            completed_challenges=row.completed_challenges,
            completed_labs=row.completed_labs,
            member_since=row.created_at,
        )
        for index, row in enumerate(rows)
    ]
    return LeaderboardPage(
        entries=entries,
        page=page,
        total_pages=total_pages,
        total_users=total_users,
    )


def get_top_users(db: Session, limit: int = 5) -> list[LeaderboardEntry]:
    """Return the top N leaderboard entries (dashboard preview)."""
    rows = db.execute(_ranked_users_query().limit(limit)).all()
    return [
        LeaderboardEntry(
            rank=index + 1,
            username=row.username,
            points=row.points,
            completed_challenges=row.completed_challenges,
            completed_labs=row.completed_labs,
            member_since=row.created_at,
        )
        for index, row in enumerate(rows)
    ]


def get_user_by_username(db: Session, username: str) -> User:
    """Return an active user by username (case-insensitive) or raise."""
    user = db.scalar(
        select(User).where(
            func.lower(User.username) == username.lower(),
            User.is_active.is_(True),
        )
    )
    if user is None:
        raise UserNotFoundError()
    return user


def get_profile_stats(db: Session, user: User) -> ProfileStats:
    """Compute profile statistics for a user with aggregate queries."""
    completed = UserChallengeProgress.is_completed.is_(True)
    points, completed_challenges, total_attempts = db.execute(
        select(
            func.coalesce(func.sum(case((completed, Challenge.points), else_=0)), 0),
            func.coalesce(func.sum(case((completed, 1), else_=0)), 0),
            func.coalesce(func.sum(UserChallengeProgress.attempts), 0),
        )
        .select_from(UserChallengeProgress)
        .join(Challenge, Challenge.id == UserChallengeProgress.challenge_id)
        .join(Lab, Lab.id == Challenge.lab_id)
        .where(
            UserChallengeProgress.user_id == user.id,
            Challenge.is_active.is_(True),
            Lab.is_active.is_(True),
        )
    ).one()

    completed_labs = (
        db.scalar(
            select(func.count())
            .select_from(UserLabProgress)
            .join(Lab, Lab.id == UserLabProgress.lab_id)
            .where(
                UserLabProgress.user_id == user.id,
                UserLabProgress.status == ProgressStatus.COMPLETED,
                Lab.is_active.is_(True),
            )
        )
        or 0
    )

    return ProfileStats(
        points=points,
        rank=get_user_rank(db, user),
        completed_labs=completed_labs,
        completed_challenges=completed_challenges,
        total_attempts=total_attempts,
    )


def get_user_rank(db: Session, user: User) -> int:
    """Return the user's 1-based global rank (0 if not ranked)."""
    points = _points_expr()
    ranked = (
        select(
            User.username,
            func.row_number()
            .over(
                order_by=(
                    func.coalesce(points.c.points, 0).desc(),
                    func.coalesce(points.c.completed_challenges, 0).desc(),
                    User.created_at.asc(),
                )
            )
            .label("rank"),
        )
        .outerjoin(points, points.c.user_id == User.id)
        .where(User.is_active.is_(True))
        .subquery()
    )
    rank = db.scalar(
        select(ranked.c.rank).where(ranked.c.username == user.username)
    )
    return rank or 0


def get_recent_activity(
    db: Session, user_id: uuid.UUID, limit: int = 10
) -> list[ActivityItem]:
    """Return the user's most recently completed challenges."""
    rows = db.execute(
        select(
            Challenge.title,
            Lab.title.label("lab_title"),
            Lab.slug,
            Challenge.points,
            UserChallengeProgress.completed_at,
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
        .order_by(UserChallengeProgress.completed_at.desc())
        .limit(limit)
    ).all()
    return [
        ActivityItem(
            challenge_title=row.title,
            lab_title=row.lab_title,
            lab_slug=row.slug,
            points=row.points,
            completed_at=row.completed_at,
        )
        for row in rows
    ]
