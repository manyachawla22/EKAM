from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID

from app.models.judge import Judge, JudgeAssignment
from app.models.event import Round
from app.models.team import Team
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
    Return all team assignments for a judge in an event, enriched with
    round/team names and whether a gradeable submission exists.
    """
    # Fetch rounds for this event
    rounds_result = await db.execute(
        select(Round).where(Round.event_id == event_id)
    )
    rounds = {r.id: r for r in rounds_result.scalars().all()}

    if not rounds:
        return []

    # Fetch this judge's assignments for any of those rounds
    assignments_result = await db.execute(
        select(JudgeAssignment).where(
            JudgeAssignment.judge_id == judge_id,
            JudgeAssignment.round_id.in_(list(rounds.keys()))
        )
    )
    assignments = assignments_result.scalars().all()

    if not assignments:
        return []

    # Batch-fetch teams
    team_ids = {a.team_id for a in assignments}
    teams_result = await db.execute(
        select(Team).where(Team.id.in_(list(team_ids)))
    )
    teams = {t.id: t for t in teams_result.scalars().all()}

    # Batch-fetch submissions for (team, round) pairs in this event
    round_ids = {a.round_id for a in assignments}
    subs_result = await db.execute(
        select(Submission).where(
            Submission.team_id.in_(list(team_ids)),
            Submission.round_id.in_(list(round_ids)),
        )
    )
    # Index by (team_id, round_id) → submission
    submissions: dict[tuple, Submission] = {}
    for s in subs_result.scalars().all():
        submissions[(s.team_id, s.round_id)] = s

    # Fetch evaluations by this judge for those submissions
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
    for a in assignments:
        rnd = rounds.get(a.round_id)
        team = teams.get(a.team_id)
        if not rnd or not team:
            continue
        sub = submissions.get((a.team_id, a.round_id))
        details.append(JudgeAssignmentDetail(
            assignment_id=a.id,
            round_id=a.round_id,
            round_name=rnd.name,
            round_status=rnd.status.value if hasattr(rnd.status, "value") else str(rnd.status),
            team_id=a.team_id,
            team_name=team.name,
            submission_id=sub.id if sub else None,
            submission_status=sub.status.value if sub and hasattr(sub.status, "value") else (str(sub.status) if sub else None),
            already_evaluated=sub.id in evaluated_sub_ids if sub else False,
        ))

    return details