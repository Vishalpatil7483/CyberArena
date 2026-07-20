"""Achievement engine: definitions, evaluation, and awarding.

Achievement rules are expressed as predicates over a user's aggregate
progress snapshot, so evaluation is one pass over cheap counters and is
naturally idempotent (already-earned achievements are skipped).
"""

import uuid
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.achievement import Achievement, UserAchievement
from app.models.challenge import Challenge, UserChallengeProgress
from app.models.lab import Lab, ProgressStatus, UserLabProgress


@dataclass(frozen=True)
class ProgressSnapshot:
    """Counters an achievement rule can depend on."""

    points: int
    completed_challenges: int
    completed_labs: int
    completed_lab_categories: frozenset[str]


@dataclass(frozen=True)
class AchievementRule:
    """A seedable achievement definition plus its earning predicate."""

    slug: str
    name: str
    description: str
    icon: str
    category: str
    points_required: int
    is_earned: Callable[[ProgressSnapshot], bool]


def _category_rule(category: str) -> Callable[[ProgressSnapshot], bool]:
    return lambda s: category in s.completed_lab_categories


ACHIEVEMENT_RULES: list[AchievementRule] = [
    AchievementRule(
        slug="first-blood",
        name="First Blood",
        description="Solve your first challenge.",
        icon="bi-droplet-fill",
        category="Milestones",
        points_required=0,
        is_earned=lambda s: s.completed_challenges >= 1,
    ),
    AchievementRule(
        slug="explorer",
        name="Explorer",
        description="Complete your first lab.",
        icon="bi-compass-fill",
        category="Milestones",
        points_required=0,
        is_earned=lambda s: s.completed_labs >= 1,
    ),
    AchievementRule(
        slug="web-apprentice",
        name="Web Apprentice",
        description="Complete your first Web Security lab.",
        icon="bi-globe2",
        category="Categories",
        points_required=0,
        is_earned=_category_rule("Web Security"),
    ),
    AchievementRule(
        slug="cryptographer",
        name="Cryptographer",
        description="Complete your first Cryptography lab.",
        icon="bi-key-fill",
        category="Categories",
        points_required=0,
        is_earned=_category_rule("Cryptography"),
    ),
    AchievementRule(
        slug="linux-explorer",
        name="Linux Explorer",
        description="Complete your first Linux lab.",
        icon="bi-terminal-fill",
        category="Categories",
        points_required=0,
        is_earned=_category_rule("Linux"),
    ),
    AchievementRule(
        slug="network-analyst",
        name="Network Analyst",
        description="Complete your first Network Security lab.",
        icon="bi-diagram-3-fill",
        category="Categories",
        points_required=0,
        is_earned=_category_rule("Network Security"),
    ),
    AchievementRule(
        slug="reverse-engineer",
        name="Reverse Engineer",
        description="Complete your first Reverse Engineering lab.",
        icon="bi-cpu-fill",
        category="Categories",
        points_required=0,
        is_earned=_category_rule("Reverse Engineering"),
    ),
    AchievementRule(
        slug="forensics-rookie",
        name="Forensics Rookie",
        description="Complete your first Digital Forensics lab.",
        icon="bi-search",
        category="Categories",
        points_required=0,
        is_earned=_category_rule("Digital Forensics"),
    ),
    AchievementRule(
        slug="100-points-club",
        name="100 Points Club",
        description="Earn 100 challenge points.",
        icon="bi-award-fill",
        category="Points",
        points_required=100,
        is_earned=lambda s: s.points >= 100,
    ),
    AchievementRule(
        slug="250-points-club",
        name="250 Points Club",
        description="Earn 250 challenge points.",
        icon="bi-trophy-fill",
        category="Points",
        points_required=250,
        is_earned=lambda s: s.points >= 250,
    ),
    AchievementRule(
        slug="500-points-club",
        name="500 Points Club",
        description="Earn 500 challenge points.",
        icon="bi-gem",
        category="Points",
        points_required=500,
        is_earned=lambda s: s.points >= 500,
    ),
]

RULES_BY_SLUG: dict[str, AchievementRule] = {r.slug: r for r in ACHIEVEMENT_RULES}


def get_progress_snapshot(db: Session, user_id: uuid.UUID) -> ProgressSnapshot:
    """Collect the counters used by achievement predicates (3 queries)."""
    completed_challenges, points = db.execute(
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

    completed_lab_rows = db.scalars(
        select(Lab.category)
        .join(UserLabProgress, UserLabProgress.lab_id == Lab.id)
        .where(
            UserLabProgress.user_id == user_id,
            UserLabProgress.status == ProgressStatus.COMPLETED,
            Lab.is_active.is_(True),
        )
    ).all()

    return ProgressSnapshot(
        points=points or 0,
        completed_challenges=completed_challenges or 0,
        completed_labs=len(completed_lab_rows),
        completed_lab_categories=frozenset(completed_lab_rows),
    )


def get_user_achievements(
    db: Session, user_id: uuid.UUID
) -> list[UserAchievement]:
    """Return the user's earned achievements, most recent first."""
    return list(
        db.scalars(
            select(UserAchievement)
            .options(joinedload(UserAchievement.achievement))
            .where(UserAchievement.user_id == user_id)
            .order_by(UserAchievement.earned_at.desc())
        )
    )


def evaluate_achievements(db: Session, user_id: uuid.UUID) -> list[Achievement]:
    """Award any newly earned achievements. Returns the new ones.

    Idempotent: already-earned achievements are never re-awarded, and the
    unique constraint guards concurrent evaluation.
    """
    snapshot = get_progress_snapshot(db, user_id)
    earned_ids = set(
        db.scalars(
            select(UserAchievement.achievement_id).where(
                UserAchievement.user_id == user_id
            )
        )
    )
    achievements = db.scalars(select(Achievement)).all()

    newly_awarded: list[Achievement] = []
    for achievement in achievements:
        if achievement.id in earned_ids:
            continue
        rule = RULES_BY_SLUG.get(achievement.slug)
        if rule is None or not rule.is_earned(snapshot):
            continue
        db.add(UserAchievement(user_id=user_id, achievement_id=achievement.id))
        try:
            db.commit()
        except IntegrityError:
            # Lost a race with a concurrent evaluation; already awarded.
            db.rollback()
            continue
        newly_awarded.append(achievement)
    return newly_awarded


def get_next_points_achievement(
    db: Session, user_id: uuid.UUID, current_points: int
) -> Achievement | None:
    """Return the nearest unearned points-based achievement."""
    earned = (
        select(UserAchievement.achievement_id)
        .where(UserAchievement.user_id == user_id)
        .scalar_subquery()
    )
    return db.scalar(
        select(Achievement)
        .where(
            Achievement.points_required > 0,
            Achievement.points_required > current_points,
            Achievement.id.notin_(earned),
        )
        .order_by(Achievement.points_required.asc())
        .limit(1)
    )
