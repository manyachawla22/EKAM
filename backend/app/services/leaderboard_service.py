from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.submission import Submission, Evaluation
from app.services.submission_service import recompute_panel_averages


async def generate_leaderboard_service(
    db: AsyncSession,
    round_id
):
    result = await db.execute(
        select(Submission).where(
            Submission.round_id == round_id
        )
    )

    submissions = list(result.scalars().all())

    # Recompute panel averages from evaluations so the ranking reflects the
    # true mean (and self-heals any stale stored values from before the
    # flush fix).
    await recompute_panel_averages(db, submissions)

    # The leaderboard is only meaningful once judging has begun: show only
    # submissions that have at least one evaluation. (An empty result means
    # "no team evaluated yet".)
    if submissions:
        evaluated_rows = await db.execute(
            select(Evaluation.submission_id)
            .where(Evaluation.submission_id.in_([s.id for s in submissions]))
            .distinct()
        )
        evaluated_ids = {row[0] for row in evaluated_rows.all()}
        submissions = [s for s in submissions if s.id in evaluated_ids]

    leaderboard = sorted(
        submissions,
        key=lambda x: x.final_score or 0,
        reverse=True
    )

    return leaderboard
