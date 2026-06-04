"""
EKAM Participant Auth Helpers

Lookup participants by email + event, validate event access.
"""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.participant import Participant
from app.models.event import Event


async def find_participant_by_email_and_event(
    db: AsyncSession,
    email: str,
    event_id: str,
) -> Participant | None:
    """Find a participant by email within a specific event.

    Email is matched case-insensitively and whitespace-trimmed: a participant
    stored as "Foo@Bar.com" must still be found when they log in as
    "  foo@bar.com ", otherwise they'd see "no account found" despite being
    listed in the event.
    """

    result = await db.execute(
        select(Participant).where(
            func.lower(func.trim(Participant.email)) == (email or "").strip().lower(),
            Participant.event_id == event_id,
        )
    )
    return result.scalars().first()


async def find_participant_by_email_and_hash(
    db: AsyncSession,
    email: str,
    event_hash: str,
) -> Participant | None:
    """
    Find a participant by email + event_hash.
    First resolves the event from its hash, then looks up the participant.

    The hash is matched case-insensitively and trimmed because the display
    hash (e.g. "EF-AB12CD") is typed by hand at login and is easy to enter in
    the wrong case.
    """

    event_result = await db.execute(
        select(Event).where(
            func.lower(func.trim(Event.hash)) == (event_hash or "").strip().lower()
        )
    )
    event = event_result.scalars().first()

    if not event:
        return None

    return await find_participant_by_email_and_event(db, email, str(event.id))


async def validate_participant_event_access(
    db: AsyncSession,
    participant_id: str,
    event_id: str,
) -> bool:
    """Check if a participant belongs to the given event."""

    result = await db.execute(
        select(Participant).where(
            Participant.id == participant_id,
            Participant.event_id == event_id,
        )
    )
    return result.scalars().first() is not None
