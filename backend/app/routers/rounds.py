from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_role

from app.models.user import User, UserRole

from app.schemas.round import (
    Round,
    RoundCreate
)

from app.services.round_service import (
    create_round_service,
    list_rounds_service
)

router = APIRouter(
    prefix="/rounds",
    tags=["Rounds"]
)


@router.post(
    "/create",
    response_model=Round,
    status_code=status.HTTP_201_CREATED
)
async def create_round(
    round_in: RoundCreate,
    current_user: User = Depends(
        require_role([
            UserRole.organizer,
            UserRole.admin
        ])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await create_round_service(
        db,
        round_in,
        current_user
    )


@router.get(
    "/{event_id}",
    response_model=List[Round]
)
async def list_rounds(
    event_id: UUID,
    current_user: User = Depends(require_role([
        UserRole.organizer,
        UserRole.admin,
        UserRole.judge,
        UserRole.participant
    ])),
    db: AsyncSession = Depends(get_db)
):
    return await list_rounds_service(
        db,
        event_id
    )