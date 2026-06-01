from fastapi import HTTPException
from sqlalchemy.future import select

from app.models.participant import Participant


async def register_participant_service(
    db,
    participant_data,
    current_user=None,
):
    """Register a participant for an event.

    Idempotent — if a Participant with the same (event_id, email) already
    exists, return that existing row instead of 400'ing. This lets the
    frontend's "Register" button double-tap without breaking the UX, and
    means a participant who re-loads the page never gets stuck in a state
    where they appear unregistered but can't register.
    """

    existing = await db.execute(
        select(Participant).where(
            Participant.event_id == participant_data.event_id,
            Participant.email == participant_data.email,
        )
    )
    existing_participant = existing.scalars().first()
    if existing_participant:
        # Merge any newly-provided non-empty optional fields onto the
        # existing row so re-submitting the form can be used to update.
        new_data = participant_data.model_dump(exclude_unset=True)
        for key, value in new_data.items():
            if key in ("event_id", "email"):
                continue
            if value not in (None, "", []):
                setattr(existing_participant, key, value)
        await db.commit()
        await db.refresh(existing_participant)
        return existing_participant

    participant = Participant(**participant_data.model_dump())
    db.add(participant)
    await db.commit()
    await db.refresh(participant)
    return participant


async def list_participants_service(
    db,
    event_id
):

    result = await db.execute(
        select(Participant).where(
            Participant.event_id == event_id
        )
    )

    return result.scalars().all()