from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.submission import Submission, SubmissionStatus, Evaluation
from app.models.event import Round
from app.services.rubric_service import list_criteria


async def submit_evaluation_service(
    db: AsyncSession,
    evaluation_data,
):
    data = evaluation_data.model_dump()

    # Fetch the submission early — needed for the rubric, status update, and
    # panel-average recalculation.
    result = await db.execute(
        select(Submission).where(Submission.id == data["submission_id"])
    )
    submission = result.scalars().first()

    # If the round has a rubric, the authoritative total is the SUM of the
    # per-criterion scores (each clamped to its max). This prevents a client
    # from sending a total that doesn't match the criterion breakdown.
    rubric_scores = data.get("rubric_scores") or {}
    if submission and rubric_scores:
        criteria = await list_criteria(db, submission.round_id, seed_if_empty=False)
        if criteria:
            total = 0.0
            for c in criteria:
                raw = rubric_scores.get(str(c.id))
                if raw is None:
                    continue
                try:
                    total += min(max(float(raw), 0.0), float(c.max_score))
                except (TypeError, ValueError):
                    continue
            data["total_score"] = total

    # Upsert: a judge may revise their score (e.g. after an anomaly alert), so
    # update their existing evaluation for this submission rather than inserting
    # a duplicate (which would skew the panel average).
    existing = (
        await db.execute(
            select(Evaluation).where(
                Evaluation.submission_id == data["submission_id"],
                Evaluation.judge_id == data["judge_id"],
            )
        )
    ).scalars().first()

    if existing:
        existing.total_score = data["total_score"]
        existing.rubric_scores = data.get("rubric_scores") or {}
        existing.feedback = data.get("feedback")
        evaluation = existing
    else:
        evaluation = Evaluation(**data)
        db.add(evaluation)

    # Flush so the just-added/updated evaluation is visible to the aggregate
    # query below. The session uses autoflush=False, so without this the
    # AVG() would be computed over the previously committed evaluations only —
    # leaving panel_average one evaluation behind (e.g. [95, 0] reporting 95).
    await db.flush()

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

        # When the round is fully evaluated, auto-propose the next stage
        # transition (human still approves) and notify the organizer.
        try:
            await _maybe_autopropose_transition(db, submission.round_id)
        except Exception as exc:
            print(f"[evaluation_service] auto-propose transition failed: {exc}")

    return evaluation


_NEXT_STAGE = {
    "registration": "team_formation",
    "team_formation": "submission",
    "submission": "evaluation",
    "evaluation": "results",
    "results": "completed",
}


async def _is_round_fully_evaluated(db: AsyncSession, round_id) -> bool:
    """True when every judge assignment for the round has a matching evaluation
    on that team's submission."""
    from app.models.judge import JudgeAssignment

    assignments = (
        await db.execute(
            select(JudgeAssignment).where(JudgeAssignment.round_id == round_id)
        )
    ).scalars().all()
    if not assignments:
        return False

    subs = (
        await db.execute(select(Submission).where(Submission.round_id == round_id))
    ).scalars().all()
    sub_by_team = {s.team_id: s.id for s in subs}
    if not sub_by_team:
        return False

    eval_rows = (
        await db.execute(
            select(Evaluation.judge_id, Evaluation.submission_id).where(
                Evaluation.submission_id.in_(list(sub_by_team.values()))
            )
        )
    ).all()
    done = {(jid, sid) for jid, sid in eval_rows}

    for a in assignments:
        sid = sub_by_team.get(a.team_id)
        if sid is None or (a.judge_id, sid) not in done:
            return False
    return True


async def _maybe_autopropose_transition(db: AsyncSession, round_id) -> None:
    """If the round is fully evaluated and no stage-transition approval is
    pending, create one and notify the organizer."""
    from app.models.approval import ApprovalRequest, ApprovalStatus, RequestType
    from app.models.event import Event
    from app.models.notification import NotificationType

    if not await _is_round_fully_evaluated(db, round_id):
        return

    round_obj = (
        await db.execute(select(Round).where(Round.id == round_id))
    ).scalars().first()
    if not round_obj:
        return

    event = (
        await db.execute(select(Event).where(Event.id == round_obj.event_id))
    ).scalars().first()
    if not event:
        return

    current_stage = getattr(event.stage, "value", str(event.stage))
    next_stage = _NEXT_STAGE.get(current_stage)
    if not next_stage:
        return

    # Don't pile up duplicate proposals.
    pending = (
        await db.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.event_id == event.id,
                ApprovalRequest.request_type == RequestType.stage_transition,
                ApprovalRequest.status == ApprovalStatus.pending,
            )
        )
    ).scalars().first()
    if pending:
        return

    from app.services.pipeline_service import propose_stage_transition
    from app.services.notification_service import create_notification

    await propose_stage_transition(
        db=db,
        event_id=str(event.id),
        requested_by=str(event.organizer_id),
        target_stage=next_stage,
        cutoff_score=0.0,
        round_id=str(round_id),
    )

    await create_notification(
        db=db,
        event_id=str(event.id),
        user_id=str(event.organizer_id),
        title="Round fully evaluated",
        message=(
            f"All assigned evaluations for '{round_obj.name}' are in. "
            f"A transition to the {next_stage.replace('_', ' ')} stage has been "
            f"proposed — review it in Approvals."
        ),
        notification_type=NotificationType.action_required,
    )


async def get_submission_evaluations_service(
    db: AsyncSession,
    submission_id,
):
    result = await db.execute(
        select(Evaluation).where(Evaluation.submission_id == submission_id)
    )
    return result.scalars().all()
