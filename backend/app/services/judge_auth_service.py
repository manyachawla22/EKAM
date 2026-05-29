"""
EKAM Judge Auth Helpers

Lookup judges by email + event, validate event access.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.judge import Judge
from app.models.event import Event


async def find_judge_by_email_and_event(
    db: AsyncSession,
    email: str,
    event_id: str,
) -> Judge | None:
    """Find a judge by email within a specific event."""

    result = await db.execute(
        select(Judge).where(
            Judge.email == email,
            Judge.event_id == event_id,
        )
    )
    return result.scalars().first()


async def find_judge_by_email_and_hash(
    db: AsyncSession,
    email: str,
    event_hash: str,
) -> Judge | None:
    """
    Find a judge by email + event_hash.
    First resolves the event from its hash, then looks up the judge.
    """

    event_result = await db.execute(
        select(Event).where(Event.hash == event_hash)
    )
    event = event_result.scalars().first()

    if not event:
        return None

    return await find_judge_by_email_and_event(db, email, str(event.id))


async def validate_judge_event_access(
    db: AsyncSession,
    judge_id: str,
    event_id: str,
) -> bool:
    """Check if a judge belongs to the given event."""

    result = await db.execute(
        select(Judge).where(
            Judge.id == judge_id,
            Judge.event_id == event_id,
        )
    )
    return result.scalars().first() is not None
