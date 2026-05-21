from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.participant import Participant
from app.schemas.participant import Participant as ParticipantSchema, ParticipantCreate

router = APIRouter()

@router.post("/register", response_model=ParticipantSchema, status_code=status.HTTP_201_CREATED)
async def register_participant(
    part_in: ParticipantCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # User can only register themselves
    if part_in.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Can only register yourself")

    # Check if already registered
    existing = await db.execute(
        select(Participant).where(Participant.user_id == current_user.id, Participant.event_id == part_in.event_id)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Already registered for this event")

    new_part = Participant(**part_in.model_dump())
    db.add(new_part)
    await db.commit()
    await db.refresh(new_part)
    return new_part

@router.get("/{event_id}", response_model=List[ParticipantSchema])
async def list_participants(
    event_id: UUID,
    current_user: User = Depends(require_role([UserRole.organizer, UserRole.judge])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Participant).where(Participant.event_id == event_id))
    return result.scalars().all()
