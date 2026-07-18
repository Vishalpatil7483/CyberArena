"""SQLAlchemy ORM models.

Import model modules here so Alembic autogenerate sees their tables.
"""

from app.core.database import Base  # noqa: F401
from app.models.lab import Lab, LabDifficulty, ProgressStatus, UserLabProgress  # noqa: F401
from app.models.user import User  # noqa: F401
