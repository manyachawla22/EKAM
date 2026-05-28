from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.submission import Submission, SubmissionStatus, Evaluation


async def submit_evaluation_service(
    db: AsyncSession,
    evaluation_data
):
    evaluation = Evaluation(**evaluation_data.model_dump())

    db.add(evaluation)

    result = await db.execute(
        select(Submission).where(
            Submission.id == evaluation.submission_id
        )
    )

    submission = result.scalars().first()

    if submission:
        submission.status = SubmissionStatus.reviewed

    await db.commit()
    await db.refresh(evaluation)

    return evaluation


async def get_submission_evaluations_service(
    db: AsyncSession,
    submission_id
):
    result = await db.execute(
        select(Evaluation).where(
            Evaluation.submission_id == submission_id
        )
    )

    return result.scalars().all()