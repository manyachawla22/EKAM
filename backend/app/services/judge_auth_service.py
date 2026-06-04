"""
EKAM Judge Auth Helpers

Lookup judges by email + event, validate event access.
"""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.judge import Judge
from app.models.event import Event


async def find_judge_by_email_and_event(
    db: AsyncSession,
    email: str,
    event_id: str,
) -> Judge | None:
    """Find a judge by email within a specific event.

    Email is matched case-insensitively and whitespace-trimmed so a judge
    stored as "Foo@Bar.com" is still found when they log in as
    "  foo@bar.com ".
    """

    result = await db.execute(
        select(Judge).where(
            func.lower(func.trim(Judge.email)) == (email or "").strip().lower(),
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

    The hash is matched case-insensitively and trimmed because the display
    hash (e.g. "EF-AB12CD") is typed by hand at login.
    """

    event_result = await db.execute(
        select(Event).where(
            func.lower(func.trim(Event.hash)) == (event_hash or "").strip().lower()
        )
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
