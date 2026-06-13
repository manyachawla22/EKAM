"""
EKAM Magic Link Service

Generates unique magic link tokens, stores them in AuthToken,
and verifies them on click-through.
"""

import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.auth import AuthToken, TokenType, OwnerType


MAGIC_LINK_EXPIRY_HOURS = 48


async def generate_magic_link(
    db: AsyncSession,
    owner_id: str,
    owner_type: str,
    event_id: str | None = None,
    redirect_path: str | None = None,
) -> str:
    """
    Generate a magic link token, store it in AuthToken, and return the full URL.

    `redirect_path` (e.g. "/judge/anomalies") is appended as a `next` param so the
    portal-login page can send the user straight to a specific page after
    authenticating, instead of the default role dashboard.
    """

    token_value = secrets.token_urlsafe(48)

    expires_at = datetime.now(timezone.utc) + timedelta(hours=MAGIC_LINK_EXPIRY_HOURS)

    auth_token = AuthToken(
        owner_id=owner_id,
        owner_type=OwnerType(owner_type),
        token=token_value,
        token_type=TokenType.MAGIC_LINK,
        expires_at=expires_at,
        is_used=False,
    )

    db.add(auth_token)
    await db.commit()

    # Build the magic link URL
    base_url = settings.FRONTEND_URL.rstrip("/")
    link = f"{base_url}/portal/login?token={token_value}"

    if event_id:
        link += f"&event_id={event_id}"

    if redirect_path:
        link += f"&next={quote(redirect_path, safe='')}"

    return link


async def verify_magic_link(
    db: AsyncSession,
    token: str,
) -> dict:
    """
    Verify a magic link token.
    Returns owner info on success, raises HTTPException on failure.
    """

    result = await db.execute(
        select(AuthToken).where(
            AuthToken.token == token,
            AuthToken.token_type == TokenType.MAGIC_LINK,
        )
    )
    auth_token = result.scalars().first()

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid magic link.",
        )

    if auth_token.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Magic link has already been used.",
        )

    if auth_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Magic link has expired.",
        )

    # Mark as used
    auth_token.is_used = True
    await db.commit()

    return {
        "owner_id": str(auth_token.owner_id),
        "owner_type": auth_token.owner_type.value,
    }
