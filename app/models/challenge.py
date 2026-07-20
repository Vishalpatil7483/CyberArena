"""Challenge and per-user challenge progress models."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.lab import Lab


class ChallengeType(str, enum.Enum):
    FLAG = "flag"
    QUIZ = "quiz"
    TEXT = "text"


class Challenge(TimestampMixin, Base):
    __tablename__ = "challenges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lab_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("labs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    challenge_type: Mapped[ChallengeType] = mapped_column(
        Enum(ChallengeType, native_enum=False, length=10),
        default=ChallengeType.FLAG,
        nullable=False,
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    flag_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    lab: Mapped["Lab"] = relationship(back_populates="challenges")
    progress_records: Mapped[list["UserChallengeProgress"]] = relationship(
        back_populates="challenge", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Challenge {self.title!r} lab={self.lab_id}>"


class UserChallengeProgress(Base):
    __tablename__ = "user_challenge_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", name="uq_user_challenge_progress"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("challenges.id", ondelete="CASCADE"), index=True, nullable=False
    )
    is_completed: Mapped[bool] = mapped_column(default=False, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    challenge: Mapped[Challenge] = relationship(back_populates="progress_records")

    def __repr__(self) -> str:
        return (
            f"<UserChallengeProgress user={self.user_id} "
            f"challenge={self.challenge_id} completed={self.is_completed}>"
        )
