"""
EKAM Leaderboard Router
"""

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_actor_type
from app.core.auth_context import AuthContext

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
    return await generate_leaderboard_service(
        db,
        round_id
    )