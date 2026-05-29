from fastapi import HTTPException
from sqlalchemy.future import select

from app.models.participant import Participant


async def register_participant_service(
    db,
    participant_data,
    current_user=None
):

    existing = await db.execute(
        select(Participant).where(
            Participant.event_id == participant_data.event_id,
            Participant.email == participant_data.email
        )
    )

    if existing.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Participant already exists"
        )

    participant = Participant(
        **participant_data.model_dump()
    )

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