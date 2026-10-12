from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BusinessRuleError, ConflictError, UnauthorizedError
from app.core.ratelimit import enforce_email_limit
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import PasswordResetToken, RefreshToken, User
from app.services.audit_service import log_action


def _issue_tokens(db: Session, user: User) -> tuple[str, str]:
    access = create_access_token(user.id)
    refresh = generate_opaque_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.jwt_refresh_expire_days),
        )
    )
    return access, refresh


def register_user(db: Session, *, name: str, email: str, password: str) -> tuple[User, str, str]:
    email = email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise ConflictError("An account with this email already exists.")

    user = User(name=name, email=email, password_hash=hash_password(password))
    db.add(user)
    db.flush()  # get user.id
    access, refresh = _issue_tokens(db, user)
    db.commit()
    return user, access, refresh


def login_user(db: Session, *, email: str, password: str) -> tuple[User, str, str]:
    enforce_email_limit("login", email)
    user = db.scalar(select(User).where(User.email == email.lower()))
    # Same error for "no such user" and "wrong password" -> no account enumeration
    if not user or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password.")
    if not user.is_active:
        raise UnauthorizedError("This account is disabled.")

    access, refresh = _issue_tokens(db, user)
    log_action(db, action="login", user_id=user.id, resource_type="user", resource_id=user.id)
    db.commit()
    return user, access, refresh


def refresh_tokens(db: Session, *, refresh_token: str) -> tuple[User, str, str]:
    """Rotation: the used refresh token is revoked and a new pair is issued."""
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )
    now = datetime.now(timezone.utc)
    if not stored or stored.revoked_at is not None or stored.expires_at < now:
        raise UnauthorizedError("Refresh token is invalid or expired.")

    user = db.get(User, stored.user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User not available.")

    stored.revoked_at = now
    access, refresh = _issue_tokens(db, user)
    db.commit()
    return user, access, refresh


def logout_user(db: Session, *, refresh_token: str) -> None:
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token))
    )
    if stored and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()


def request_password_reset(db: Session, *, email: str) -> str | None:
    """Returns the raw token, or None if there is no such active user. The route never reveals which."""
    enforce_email_limit("reset", email)
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active:
        return None

    now = datetime.now(timezone.utc)
    # Only the newest link works: invalidate older unused ones.
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    token = generate_opaque_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=now + timedelta(minutes=settings.password_reset_expire_minutes),
        )
    )
    log_action(db, action="password_reset_requested", user_id=user.id,
               resource_type="user", resource_id=user.id)
    db.commit()
    return token


def reset_password(db: Session, *, token: str, new_password: str) -> None:
    stored = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token))
    )
    now = datetime.now(timezone.utc)
    if stored is None or stored.used_at is not None or stored.expires_at < now:
        raise BusinessRuleError("This reset link is invalid or has expired. Request a new one.")

    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise BusinessRuleError("This reset link is invalid or has expired. Request a new one.")

    user.password_hash = hash_password(new_password)
    stored.used_at = now
    # A password reset must sign the user out everywhere.
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    log_action(db, action="password_reset_completed", user_id=user.id,
               resource_type="user", resource_id=user.id)
    db.commit()
