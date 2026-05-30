"""
EKAM Authentication Service

Handles all high-level authentication workflows:
- login_service: Organizer/Admin login via Firebase
- request_access_service: Participant/Judge requests OTP via email + event_hash
- verify_otp_service: Verifies OTP and issues JWT session
- magic_login_service: Verifies magic link and issues JWT session
- refresh_service: Refreshes JWT session
- logout_service: Revokes active session
- me_service: Returns current actor profile
"""

from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.auth_context import AuthContext
from app.models.user import User, UserRole

from app.services.jwt_service import create_session, refresh_session, revoke_session
from app.services.otp_service import generate_and_store_otp, verify_otp
from app.services.magic_link_service import verify_magic_link
from app.services.email_service import send_otp_email

from app.services.participant_auth_service import find_participant_by_email_and_hash
from app.services.judge_auth_service import find_judge_by_email_and_hash


# =========================================================
# ORGANIZER / ADMIN (FIREBASE)
# =========================================================

async def login_with_profile_service(
    db: AsyncSession,
    token_data: dict,
    ip_address: str | None = None,
    user_agent: str | None = None,
    display_name: str | None = None,
) -> Dict[str, Any]:
    """
    Handle organizer login and return EKAM token merged with user profile.
    Used by the /auth/login frontend-facing endpoint.
    """
    if display_name and not token_data.get("name"):
        token_data = {**token_data, "name": display_name}

    user = await login_service(db, token_data)

    session = await create_session(
        db=db,
        owner_id=str(user.id),
        owner_type=user.role.value,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return {
        **session,
        "name": user.name or "",
        "email": user.email or "",
        "role": user.role.value,
        "organization": user.organization,
    }


async def login_service(
    db: AsyncSession,
    token_data: dict
) -> User:
    """Handle Organizer/Admin login via Firebase ID token."""

    uid = token_data.get("uid")
    email = token_data.get("email") or ""
    firebase_name = token_data.get("name") or token_data.get("display_name")

    # Primary lookup: by firebase_uid
    result = await db.execute(select(User).where(User.firebase_uid == uid))
    user = result.scalars().first()

    if not user:
        # Fallback: email match (handles account deletion + recreation in Firebase
        # where the same email gets a new UID, causing a duplicate-key INSERT).
        email_result = await db.execute(select(User).where(User.email == email))
        user = email_result.scalars().first()

        if user:
            # Re-link the existing EKAM account to the new Firebase UID.
            user.firebase_uid = uid
            user.last_login = datetime.now(timezone.utc)
        else:
            user = User(
                firebase_uid=uid,
                email=email,
                name=firebase_name or email.split("@")[0],
                role=UserRole.organizer,
                last_login=datetime.now(timezone.utc)
            )
            db.add(user)
    else:
        user.last_login = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    return user


# =========================================================
# PARTICIPANT / JUDGE (OTP & MAGIC LINK)
# =========================================================

async def request_access_service(
    db: AsyncSession,
    email: str,
    event_hash: str,
) -> Dict[str, str]:
    """
    Find participant or judge by email + event_hash.
    Generate OTP and send email.
    """

    actor = None
    actor_type = None

    # Try participant first
    actor = await find_participant_by_email_and_hash(db, email, event_hash)
    if actor:
        actor_type = "participant"
    else:
        # Try judge
        actor = await find_judge_by_email_and_hash(db, email, event_hash)
        if actor:
            actor_type = "judge"

    if not actor or not actor_type:
        # Prevent email enumeration by returning a generic success message
        # even if not found (in a production environment). For MVP, we can be explicit.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found for this email in this event."
        )

    otp = await generate_and_store_otp(db, str(actor.id), actor_type)
    
    # Send email (using our stubbed email service)
    await send_otp_email(email, otp)

    return {"message": "If an account exists, an OTP has been sent."}


async def verify_otp_service(
    db: AsyncSession,
    email: str,
    event_hash: str,
    otp: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Dict[str, Any]:
    """Verify OTP and issue JWT session."""

    actor = None
    actor_type = None

    actor = await find_participant_by_email_and_hash(db, email, event_hash)
    if actor:
        actor_type = "participant"
    else:
        actor = await find_judge_by_email_and_hash(db, email, event_hash)
        if actor:
            actor_type = "judge"

    if not actor or not actor_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found."
        )

    # Throws HTTPException if invalid
    await verify_otp(db, str(actor.id), actor_type, otp)

    # Issue session
    return await create_session(
        db=db,
        owner_id=str(actor.id),
        owner_type=actor_type,
        event_id=str(actor.event_id),
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def magic_login_service(
    db: AsyncSession,
    token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Dict[str, Any]:
    """Verify Magic Link and issue JWT session."""
    
    # Throws HTTPException if invalid
    owner_info = await verify_magic_link(db, token)
    
    owner_id = owner_info["owner_id"]
    owner_type = owner_info["owner_type"]
    
    # Need to look up event_id from the entity
    event_id = None
    if owner_type == "participant":
        from app.models.participant import Participant
        res = await db.execute(select(Participant).where(Participant.id == owner_id))
        entity = res.scalars().first()
        if entity: event_id = str(entity.event_id)
    elif owner_type == "judge":
        from app.models.judge import Judge
        res = await db.execute(select(Judge).where(Judge.id == owner_id))
        entity = res.scalars().first()
        if entity: event_id = str(entity.event_id)

    return await create_session(
        db=db,
        owner_id=owner_id,
        owner_type=owner_type,
        event_id=event_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )


# =========================================================
# SESSION MANAGEMENT
# =========================================================

async def refresh_service(
    db: AsyncSession,
    refresh_token: str,
) -> Dict[str, Any]:
    """Refresh an active JWT session."""
    return await refresh_session(db, refresh_token)


async def logout_service(
    db: AsyncSession,
    session_id: str | None,
) -> Dict[str, str]:
    """Revoke the current session."""
    if not session_id:
        return {"message": "Logged out (no active session)"}
        
    await revoke_session(db, session_id)
    return {"message": "Successfully logged out"}


# =========================================================
# PROFILE
# =========================================================

async def me_service(
    auth: AuthContext
) -> Dict[str, Any]:
    """Return the profile for the currently authenticated actor."""

    # MeResponse declares `profile: Any` — Pydantic v2 can't serialize a raw
    # SQLAlchemy ORM object behind that, so flatten the entity to a plain
    # dict of column values before returning.
    entity = auth.entity
    profile: Dict[str, Any] = {}
    if entity is not None:
        try:
            mapper = entity.__class__.__mapper__  # SQLAlchemy mapper
            for col in mapper.columns:
                val = getattr(entity, col.key, None)
                # Convert UUIDs and enums to JSON-safe primitives
                if hasattr(val, "value") and not isinstance(val, (str, int, float, bool)):
                    val = val.value
                profile[col.key] = val
        except Exception:
            profile = {}

    return {
        "id": auth.actor_id,
        "actor_type": auth.actor_type,
        "event_id": auth.event_id,
        "profile": profile,
        "permissions": [
            p.value if hasattr(p, "value") else p for p in (auth.permissions or [])
        ],
        "is_event_scoped": auth.is_event_scoped,
    }