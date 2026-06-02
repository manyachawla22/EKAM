from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.submission import Submission, Evaluation


async def recompute_panel_averages(db: AsyncSession, submissions) -> bool:
    """Recompute panel_average/final_score for the given submissions from their
    evaluations and persist any corrections.

    Self-heals rows whose stored average drifted (e.g. written before the
    flush fix). Returns True if anything changed. Safe no-op when there are no
    submissions or evaluations.
    """
    subs = list(submissions)
    if not subs:
        return False

    sub_ids = [s.id for s in subs]
    rows = (
        await db.execute(
            select(
                Evaluation.submission_id,
                func.avg(Evaluation.total_score),
            )
            .where(Evaluation.submission_id.in_(sub_ids))
            .group_by(Evaluation.submission_id)
        )
    ).all()
    avg_by_submission = {
        sid: float(avg) for sid, avg in rows if avg is not None
    }

    changed = False
    for submission in subs:
        avg = avg_by_submission.get(submission.id)
        if avg is None:
            continue
        if submission.panel_average != avg or submission.final_score != avg:
            submission.panel_average = avg
            submission.final_score = avg
            changed = True

    if changed:
        await db.commit()

    return changed


async def get_submission_service(
    db: AsyncSession,
    submission_id,
):
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalars().first()

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    return submission


async def create_submission_service(
    db: AsyncSession,
    submission_data
):
    data = submission_data.model_dump()

    # A team has a single submission per round. Re-submitting updates the
    # existing row instead of creating a duplicate — duplicates were showing up
    # twice for organizers and splitting judges across different rows (so their
    # scores never landed on the same submission for the panel average).
    existing = (
        await db.execute(
            select(Submission).where(
                Submission.team_id == data["team_id"],
                Submission.round_id == data["round_id"],
            )
        )
    ).scalars().first()

    if existing:
        existing.attachments = data.get("attachments") or []
        await db.commit()
        await db.refresh(existing)
        return existing

    submission = Submission(**data)

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

    submissions = result.scalars().all()

    # Self-heal any stale panel averages (e.g. written before the flush fix).
    await recompute_panel_averages(db, submissions)

    return submissions