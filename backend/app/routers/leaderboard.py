from uuid import UUID

from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_role

from app.models.user import (
    User,
    UserRole
)

from app.services.leaderboard_service import (
    generate_leaderboard_service
)

router = APIRouter(
    prefix="/leaderboard",
    tags=["Leaderboard"]
)


@router.get("/{round_id}")
async def get_leaderboard(
    round_id: UUID,
    current_user: User = Depends(
        require_role([
            UserRole.organizer,
            UserRole.admin
        ])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await generate_leaderboard_service(
        db,
        round_id
    )