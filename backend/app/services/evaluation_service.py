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
    
    # Trigger anomaly detection (Phase 8)
    from app.services.anomaly_service import analyze_evaluation
    # Since we need event_id, we pull it from the submission's event_id (or similar logic). 
    # For now, we will pass a placeholder event_id or assume it's attached.
    # Note: submission should ideally link to event.
    await analyze_evaluation(db, "00000000-0000-0000-0000-000000000000", evaluation)

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