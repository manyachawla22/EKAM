"""
EKAM Participant Auth Helpers

Lookup participants by email + event, validate event access.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.participant import Participant
from app.models.event import Event


async def find_participant_by_email_and_event(
    db: AsyncSession,
    email: str,
    event_id: str,
) -> Participant | None:
    """Find a participant by email within a specific event."""

    result = await db.execute(
        select(Participant).where(
            Participant.email == email,
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
    """

    event_result = await db.execute(
        select(Event).where(Event.hash == event_hash)
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
