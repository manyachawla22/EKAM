from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.event import Event
from app.models.participant import Participant
from app.models.judge import JudgeAssignment
from app.models.submission import Submission


async def organizer_dashboard_service(
    db: AsyncSession,
    event_id,
    current_user
):
    participants = await db.execute(
        select(Participant).where(
            Participant.event_id == event_id
        )
    )

    submissions = await db.execute(
        select(Submission)
    )

    return {
        "participants": participants.scalars().all(),
        "submissions": submissions.scalars().all()
    }


async def participant_dashboard_service(
    db: AsyncSession,
    event_id,
    current_user
):
    submissions = await db.execute(
        select(Submission)
    )

    return {
        "submissions": submissions.scalars().all()
    }


async def judge_dashboard_service(
    db: AsyncSession,
    event_id,
    current_user
):
    assignments = await db.execute(
        select(JudgeAssignment)
    )

    return {
        "assignments": assignments.scalars().all()
    }