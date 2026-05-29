from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.submission import Submission, SubmissionStatus, Evaluation
from app.models.event import Round


async def submit_evaluation_service(
    db: AsyncSession,
    evaluation_data,
):
    evaluation = Evaluation(**evaluation_data.model_dump())
    db.add(evaluation)

    # Fetch the submission to update its status and recalculate panel average
    result = await db.execute(
        select(Submission).where(Submission.id == evaluation.submission_id)
    )
    submission = result.scalars().first()

    if submission:
        submission.status = SubmissionStatus.reviewed

        # Recalculate panel average from all evaluations for this submission
        res_scores = await db.execute(
            select(func.avg(Evaluation.total_score)).where(
                Evaluation.submission_id == submission.id
            )
        )
        avg = res_scores.scalar()
        if avg is not None:
            submission.panel_average = float(avg)
            submission.final_score = float(avg)

    await db.commit()
    await db.refresh(evaluation)

    # Derive real event_id through Round to trigger anomaly detection
    if submission:
        try:
            res_round = await db.execute(
                select(Round).where(Round.id == submission.round_id)
            )
            round_obj = res_round.scalars().first()
            if round_obj and round_obj.event_id:
                from app.services.anomaly_service import analyze_evaluation
                await analyze_evaluation(db, str(round_obj.event_id), evaluation)
        except Exception as exc:
            # Anomaly detection must never block evaluation submission
            print(f"[evaluation_service] anomaly detection failed: {exc}")

    return evaluation


async def get_submission_evaluations_service(
    db: AsyncSession,
    submission_id,
):
    result = await db.execute(
        select(Evaluation).where(Evaluation.submission_id == submission_id)
    )
    return result.scalars().all()
