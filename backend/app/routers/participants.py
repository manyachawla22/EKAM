from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_role

from app.models.user import User, UserRole

from app.schemas.participant import (
    Participant,
    ParticipantCreate
)

from app.services.participant_service import (
    register_participant_service,
    list_participants_service
)

router = APIRouter(
    prefix="/participants",
    tags=["Participants"]
)


@router.post(
    "/register",
    response_model=Participant,
    status_code=status.HTTP_201_CREATED
)
async def register_participant(
    participant_in: ParticipantCreate,
    current_user: User = Depends(
        require_role([UserRole.organizer, UserRole.admin])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await register_participant_service(
        db,
        participant_in,
        current_user
    )


@router.get("/{event_id}", response_model=List[Participant])
async def list_participants(
    event_id: UUID,
    current_user: User = Depends(
        require_role([
            UserRole.organizer,
            UserRole.admin,
            UserRole.judge
        ])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await list_participants_service(
        db,
        event_id
    )