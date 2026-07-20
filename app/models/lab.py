"""Lab and per-user lab progress models."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.challenge import Challenge


class LabDifficulty(str, enum.Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class ProgressStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Lab(TimestampMixin, Base):
    __tablename__ = "labs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(140), unique=True, index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[LabDifficulty] = mapped_column(
        Enum(LabDifficulty, native_enum=False, length=10), nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    estimated_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    progress_records: Mapped[list["UserLabProgress"]] = relationship(
        back_populates="lab", cascade="all, delete-orphan"
    )
    challenges: Mapped[list["Challenge"]] = relationship(
        back_populates="lab", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Lab {self.slug!r}>"


class UserLabProgress(Base):
    __tablename__ = "user_lab_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lab_id", name="uq_user_lab_progress"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lab_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("labs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[ProgressStatus] = mapped_column(
        Enum(ProgressStatus, native_enum=False, length=12),
        default=ProgressStatus.IN_PROGRESS,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    lab: Mapped[Lab] = relationship(back_populates="progress_records")

    def __repr__(self) -> str:
        return (
            f"<UserLabProgress user={self.user_id} lab={self.lab_id} "
            f"{self.status.value}>"
        )
