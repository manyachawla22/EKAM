from fastapi import HTTPException
from sqlalchemy.future import select

from app.models.participant import Participant


class ParticipantService:

    @staticmethod
    async def register_participant(
        db,
        participant_data
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


    @staticmethod
    async def list_participants(
        db,
        event_id
    ):

        result = await db.execute(
            select(Participant).where(
                Participant.event_id == event_id
            )
        )

        return result.scalars().all()