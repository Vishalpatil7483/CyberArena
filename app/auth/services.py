"""Authentication business logic."""

import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    PASSWORD_MAX_BYTES,
    dummy_verify,
    hash_password,
    verify_password,
)
from app.models.user import User

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,50}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LENGTH = 8


class DuplicateUserError(Exception):
    """Raised when a username or email is already registered."""


def validate_registration(
    username: str,
    email: str,
    password: str,
    password_confirm: str,
) -> list[str]:
    """Return a list of human-readable validation errors (empty if valid)."""
    errors: list[str] = []
    if not USERNAME_RE.match(username):
        errors.append(
            "Username must be 3-50 characters using only letters, "
            "numbers, and underscores."
        )
    if not EMAIL_RE.match(email) or len(email) > 255:
        errors.append("Enter a valid email address.")
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."
        )
    elif len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        errors.append(
            f"Password must be at most {PASSWORD_MAX_BYTES} bytes long."
        )
    if password != password_confirm:
        errors.append("Passwords do not match.")
    return errors


def username_taken(db: Session, username: str) -> bool:
    return (
        db.scalar(
            select(User.id).where(func.lower(User.username) == username.lower())
        )
        is not None
    )


def email_taken(db: Session, email: str) -> bool:
    return (
        db.scalar(select(User.id).where(func.lower(User.email) == email.lower()))
        is not None
    )


def register_user(db: Session, username: str, email: str, password: str) -> User:
    """Create a new user with a hashed password.

    Raises DuplicateUserError if the username or email is already taken —
    including the race where a concurrent request registered it between
    the pre-check and this insert.
    """
    user = User(
        username=username,
        email=email.lower(),
        password_hash=hash_password(password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateUserError() from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, identifier: str, password: str) -> User | None:
    """Authenticate by username or email. Returns the user or None.

    Deliberately gives no indication of which part failed, and burns the
    same bcrypt time for unknown users so response timing does not reveal
    whether an account exists.
    """
    lowered = identifier.lower()
    user = db.scalar(
        select(User).where(
            (func.lower(User.username) == lowered)
            | (func.lower(User.email) == lowered)
        )
    )
    if user is None:
        dummy_verify()
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)
