from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.submission import Submission


async def create_submission_service(
    db: AsyncSession,
    submission_data
):
    submission = Submission(**submission_data.model_dump())

    db.add(submission)

    await db.commit()
    await db.refresh(submission)

    return submission


async def list_submissions_service(
    db: AsyncSession,
    round_id
):
    result = await db.execute(
        select(Submission).where(
            Submission.round_id == round_id
        )
    )

    return result.scalars().all()