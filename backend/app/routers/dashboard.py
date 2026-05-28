from uuid import UUID

from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import get_current_user

from app.models.user import User

from app.services.dashboard_service import (
    organizer_dashboard_service,
    participant_dashboard_service,
    judge_dashboard_service
)

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/organizer/{event_id}")
async def organizer_dashboard(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await organizer_dashboard_service(
        db,
        event_id,
        current_user
    )


@router.get("/participant/{event_id}")
async def participant_dashboard(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await participant_dashboard_service(
        db,
        event_id,
        current_user
    )


@router.get("/judge/{event_id}")
async def judge_dashboard(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await judge_dashboard_service(
        db,
        event_id,
        current_user
    )