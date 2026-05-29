"""
EKAM JWT Session Service

Manages the lifecycle of user sessions:
- create_session: creates a DB session record + returns access/refresh tokens
- refresh_session: validates refresh token and issues a new access token
- revoke_session: marks a session as inactive
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    verify_jwt,
    decode_token_payload,
)

from app.models.auth import UserSession


async def create_session(
    db: AsyncSession,
    owner_id: str,
    owner_type: str,
    event_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """
    Create a new session in the DB and return access + refresh tokens.
    """

    session_id = str(uuid4())

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    # Persist session record
    session = UserSession(
        owner_id=owner_id,
        owner_type=owner_type,
        jwt_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Issue tokens
    access = create_access_token(
        actor_id=owner_id,
        actor_type=owner_type,
        event_id=event_id,
        session_id=session_id,
    )

    refresh = create_refresh_token(
        actor_id=owner_id,
        actor_type=owner_type,
        session_id=session_id,
        event_id=event_id,
    )

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "actor_type": owner_type,
        "event_id": event_id,
        "session_id": str(session.id),
    }


async def refresh_session(
    db: AsyncSession,
    refresh_token: str,
) -> dict:
    """
    Validate a refresh token and issue a new access token.
    The refresh token itself is NOT rotated (simple rotation strategy).
    """

    payload = verify_jwt(refresh_token)

    if payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not a refresh token",
        )

    session_id = payload.get("jti")

    # Verify session is still active in DB
    result = await db.execute(
        select(UserSession).where(
            UserSession.jwt_id == session_id,
            UserSession.is_active == True,
        )
    )
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or revoked",
        )

    # Issue new access token
    access = create_access_token(
        actor_id=payload["sub"],
        actor_type=payload["actor_type"],
        event_id=payload.get("event_id"),
        session_id=session_id,
    )

    return {
        "access_token": access,
        "token_type": "bearer",
        "actor_type": payload["actor_type"],
        "event_id": payload.get("event_id"),
    }


async def revoke_session(
    db: AsyncSession,
    session_id: str,
) -> bool:
    """Mark a session as inactive (logout)."""

    result = await db.execute(
        select(UserSession).where(
            UserSession.jwt_id == session_id,
        )
    )
    session = result.scalars().first()

    if not session:
        return False

    session.is_active = False
    await db.commit()

    return True


async def revoke_all_sessions(
    db: AsyncSession,
    owner_id: str,
) -> int:
    """Revoke all active sessions for an owner. Returns count revoked."""

    result = await db.execute(
        select(UserSession).where(
            UserSession.owner_id == owner_id,
            UserSession.is_active == True,
        )
    )
    sessions = result.scalars().all()

    count = 0
    for s in sessions:
        s.is_active = False
        count += 1

    if count:
        await db.commit()

    return count
