import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID

from app.models.judge import Judge, JudgeAssignment
from app.models.event import Round
from app.models.team import Team
from app.models.match import Match
from app.models.submission import Submission, Evaluation
from app.schemas.judge import JudgeAssignmentDetail


async def create_judge_service(
    db: AsyncSession,
    judge_data,
    current_user=None
):

    existing = await db.execute(
        select(Judge).where(
            Judge.event_id == judge_data.event_id,
            Judge.email == judge_data.email
        )
    )

    if existing.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Judge already registered"
        )

    judge = Judge(
        **judge_data.model_dump()
    )

    db.add(judge)

    await db.commit()
    await db.refresh(judge)

    return judge


async def list_judges_service(
    db: AsyncSession,
    event_id
):

    result = await db.execute(
        select(Judge).where(
            Judge.event_id == event_id
        )
    )

    return result.scalars().all()


async def get_judge_by_id_service(
    db: AsyncSession,
    judge_id: str
):
    result = await db.execute(
        select(Judge).where(
            Judge.id == judge_id
        )
    )

    return result.scalars().first()


async def get_judge_assignments_detail(
    db: AsyncSession,
    event_id: UUID,
    judge_id: UUID,
) -> list[JudgeAssignmentDetail]:
    """
    Return this judge's gradeable rows for an event — one per (assigned team,
    round), enriched with round/team names and the round's own submission.

    A judge assignment is treated as *panel membership*: the judge grades the
    same teams in every round. The auto-assigner only ever stores assignments
    under a single (arbitrary) round, so keying the dashboard off the stored
    round_id meant a judge in a multi-round event could only see — and only
    grade — that one round's submission, showing the wrong round's data. We
    instead derive the panel teams from the assignments and fan them out across
    every round of the event, pairing each with that round's submission.
    """
    # Fetch rounds for this event, oldest first so the dashboard lists them in
    # a stable, chronological order.
    rounds_result = await db.execute(
        select(Round)
        .where(Round.event_id == event_id)
        .order_by(Round.created_at, Round.id)
    )
    rounds = rounds_result.scalars().all()

    if not rounds:
        return []

    # The judge's assignments determine which teams form their panel. The
    # round_id stored on each row is intentionally ignored here — the panel
    # applies to every round (see docstring).
    assignments_result = await db.execute(
        select(JudgeAssignment).where(
            JudgeAssignment.judge_id == judge_id,
            JudgeAssignment.round_id.in_([r.id for r in rounds]),
        )
    )
    assignments = assignments_result.scalars().all()

    if not assignments:
        return []

    # Rounds that have a tournament bracket (Match rows) are scored through the
    # referee bracket card, not a participant submission — flag them so the judge
    # dashboard doesn't show "awaiting submission" for a live match.
    bracket_round_ids = set((await db.execute(
        select(Match.round_id).where(Match.round_id.in_([r.id for r in rounds])).distinct()
    )).scalars().all())

    panel_team_ids = {a.team_id for a in assignments}
    # Reuse the real assignment row id when one exists for a (team, round) pair;
    # otherwise synthesize a deterministic id (the frontend only uses it as a
    # list key, but the schema requires a UUID).
    real_assignment_id = {(a.team_id, a.round_id): a.id for a in assignments}

    # Batch-fetch the panel's teams.
    teams_result = await db.execute(
        select(Team).where(Team.id.in_(list(panel_team_ids)))
    )
    teams = {t.id: t for t in teams_result.scalars().all()}

    # Batch-fetch every submission for (panel team, any round) in this event.
    subs_result = await db.execute(
        select(Submission).where(
            Submission.team_id.in_(list(panel_team_ids)),
            Submission.round_id.in_([r.id for r in rounds]),
        )
    )
    submissions: dict[tuple, Submission] = {}
    for s in subs_result.scalars().all():
        submissions[(s.team_id, s.round_id)] = s

    # Fetch evaluations by this judge for those submissions.
    sub_ids = {s.id for s in submissions.values()}
    evaluated_sub_ids: set = set()
    if sub_ids:
        evals_result = await db.execute(
            select(Evaluation.submission_id).where(
                Evaluation.submission_id.in_(list(sub_ids)),
                Evaluation.judge_id == judge_id,
            )
        )
        evaluated_sub_ids = {row[0] for row in evals_result.all()}

    details: list[JudgeAssignmentDetail] = []
    for rnd in rounds:
        round_status = rnd.status.value if hasattr(rnd.status, "value") else str(rnd.status)
        for team_id in panel_team_ids:
            team = teams.get(team_id)
            if not team:
                continue
            sub = submissions.get((team_id, rnd.id))
            assignment_id = real_assignment_id.get((team_id, rnd.id)) or uuid.uuid5(
                uuid.NAMESPACE_URL, f"{judge_id}:{team_id}:{rnd.id}"
            )
            # Blind review (5b): hide author identity in an anonymous round.
            team_name = (
                f"Submission #{str(sub.id if sub else team.id)[:6].upper()}"
                if getattr(rnd, "anonymous", False)
                else team.name
            )
            details.append(JudgeAssignmentDetail(
                assignment_id=assignment_id,
                round_id=rnd.id,
                round_name=rnd.name,
                round_status=round_status,
                team_id=team_id,
                team_name=team_name,
                submission_id=sub.id if sub else None,
                submission_status=sub.status.value if sub and hasattr(sub.status, "value") else (str(sub.status) if sub else None),
                already_evaluated=sub.id in evaluated_sub_ids if sub else False,
                is_bracket=rnd.id in bracket_round_ids,
            ))

    return details