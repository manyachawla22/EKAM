"""
EKAM Leaderboard Router
"""

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db

from app.middleware.auth import require_actor_type
from app.core.auth_context import AuthContext

from app.models.match import Match
from app.services import bracket_service
from app.services.leaderboard_service import (
    generate_leaderboard_service
)

router = APIRouter(
    prefix="/leaderboard",
    tags=["Leaderboard"]
)


@router.get(
    "/{round_id}",
    dependencies=[Depends(require_actor_type(["organizer", "judge", "participant"]))]
)
async def get_leaderboard(
    round_id: UUID,
    auth: AuthContext = Depends(require_actor_type(["organizer", "judge", "participant"])),
    db: AsyncSession = Depends(get_db)
):
    # Depending on visibility rules, we might restrict participants from seeing certain leaderboards.
    # We will refine this in Phase 8 (Leaderboard).
    # Tournament rounds are scored on the bracket, not submissions — rank by how
    # far each contestant advanced so the leaderboard reflects the bracket result.
    is_bracket = (await db.execute(
        select(Match.id).where(Match.round_id == round_id).limit(1)
    )).scalars().first()
    if is_bracket is not None:
        return await bracket_service.bracket_standings(db, round_id)

    return await generate_leaderboard_service(
        db,
        round_id
    )