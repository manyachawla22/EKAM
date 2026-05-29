"""
EKAM JWT Token Utilities

Creates and verifies EKAM-issued JWTs for all actor types
(organizer, admin, participant, judge).
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Optional

from jose import jwt, JWTError
from fastapi import HTTPException, status

from app.core.config import settings


def create_access_token(
    actor_id: str,
    actor_type: str,
    event_id: Optional[str] = None,
    session_id: Optional[str] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """Create a short-lived access token."""

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(actor_id),
        "actor_type": actor_type,
        "jti": session_id or str(uuid4()),
        "iat": now,
        "exp": expire,
        "token_type": "access",
    }

    if event_id:
        payload["event_id"] = str(event_id)

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    actor_id: str,
    actor_type: str,
    session_id: Optional[str] = None,
    event_id: Optional[str] = None,
) -> str:
    """Create a long-lived refresh token."""

    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(actor_id),
        "actor_type": actor_type,
        "jti": session_id or str(uuid4()),
        "iat": now,
        "exp": expire,
        "token_type": "refresh",
    }

    if event_id:
        payload["event_id"] = str(event_id)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def verify_jwt(token: str) -> dict:
    """
    Decode and verify an EKAM JWT.
    Returns the decoded payload dict.
    Raises HTTPException on invalid/expired tokens.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_token_payload(token: str) -> dict | None:
    """
    Raw decode without verification (e.g. to inspect expired tokens).
    Returns None on failure.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
    except JWTError:
        return None
