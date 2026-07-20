"""SQLAlchemy ORM models.

Import model modules here so Alembic autogenerate sees their tables.
"""

from app.core.database import Base  # noqa: F401
from app.models.achievement import Achievement, UserAchievement  # noqa: F401
from app.models.challenge import Challenge, ChallengeType, UserChallengeProgress  # noqa: F401
from app.models.lab import Lab, LabDifficulty, ProgressStatus, UserLabProgress  # noqa: F401
from app.models.user import User  # noqa: F401
