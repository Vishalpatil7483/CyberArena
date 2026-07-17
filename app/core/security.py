"""Password hashing and CSRF helpers."""

import hmac
import secrets

from passlib.context import CryptContext
from starlette.requests import Request

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt only uses the first 72 bytes of a password; reject longer input
# instead of silently truncating.
PASSWORD_MAX_BYTES = 72

CSRF_SESSION_KEY = "csrf_token"
SESSION_USER_KEY = "user_id"

# Pre-computed hash of an unused random password. Verified against when a
# login names an unknown user so response timing does not reveal whether
# the account exists.
_DUMMY_HASH = pwd_context.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    return pwd_context.verify(password, password_hash)


def dummy_verify() -> None:
    """Burn the same time as a real password check (timing-attack defense)."""
    pwd_context.verify("incorrect-password", _DUMMY_HASH)


def get_csrf_token(request: Request) -> str:
    """Return the session's CSRF token, creating one if missing."""
    token = request.session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token(request: Request, submitted_token: str | None) -> bool:
    """Compare a submitted CSRF token against the session token."""
    session_token = request.session.get(CSRF_SESSION_KEY)
    if not session_token or not submitted_token:
        return False
    # compare_digest raises TypeError on non-ASCII str input; compare bytes.
    return hmac.compare_digest(
        session_token.encode("utf-8"), submitted_token.encode("utf-8")
    )
