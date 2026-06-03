from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.submission import Submission, Evaluation
from app.models.event import Round
from app.models.pipeline import EventPipeline


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
        select(Submission)
        .options(selectinload(Submission.team))
        .where(Submission.id == submission_id)
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

    # Block teams that were eliminated in a previous round from submitting.
    round_obj = (
        await db.execute(select(Round).where(Round.id == data["round_id"]))
    ).scalars().first()
    if round_obj and round_obj.event_id:
        pipeline = (
            await db.execute(
                select(EventPipeline).where(EventPipeline.event_id == round_obj.event_id)
            )
        ).scalars().first()
        if pipeline:
            eliminated = (pipeline.data or {}).get("eliminated_team_ids", [])
            if str(data["team_id"]) in eliminated:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your team did not advance and can no longer submit for this event.",
                )

        # The submission window for this round closes once the pipeline moves
        # past its submission step.
        from app.services.pipeline_service import is_round_submission_closed

        if await is_round_submission_closed(db, round_obj.event_id, round_obj.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Submissions for this round are closed.",
            )

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
        await db.refresh(existing, attribute_names=["team"])
        await _autopropose_after_submission(db, round_obj)
        return existing

    submission = Submission(**data)

    db.add(submission)

    await db.commit()
    await db.refresh(submission, attribute_names=["team"])

    await _autopropose_after_submission(db, round_obj)

    return submission


async def _autopropose_after_submission(db: AsyncSession, round_obj) -> None:
    """When all active teams have submitted for the round, the pipeline
    auto-proposes the next transition. Best-effort."""
    if not round_obj or not round_obj.event_id:
        return
    try:
        from app.services.pipeline_service import autopropose
        await autopropose(db, str(round_obj.event_id))
    except Exception as exc:
        print(f"[submission_service] autopropose failed: {exc}")


async def list_submissions_service(
    db: AsyncSession,
    round_id
):
    result = await db.execute(
        select(Submission)
        .options(selectinload(Submission.team))
        .where(Submission.round_id == round_id)
    )

    submissions = result.scalars().all()

    # Self-heal any stale panel averages (e.g. written before the flush fix).
    await recompute_panel_averages(db, submissions)

    return submissions