from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.submission import Submission


async def generate_leaderboard_service(
    db: AsyncSession,
    round_id
):
    result = await db.execute(
        select(Submission).where(
            Submission.round_id == round_id
        )
    )

    submissions = result.scalars().all()

    leaderboard = sorted(
        submissions,
        key=lambda x: x.final_score or 0,
        reverse=True
    )

    return leaderboard