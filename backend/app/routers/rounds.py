from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.middleware.auth import require_role, get_current_user
from app.models.user import User, UserRole
from app.models.event import Round, Event
from app.schemas.event import Round as RoundSchema, RoundCreate

router = APIRouter()

@router.post("/create", response_model=RoundSchema, status_code=status.HTTP_201_CREATED)
async def create_round(
    round_in: RoundCreate,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    # Verify event belongs to organizer
    event_result = await db.execute(select(Event).where(Event.id == round_in.event_id))
    event = event_result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    if event.organizer_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized to create rounds for this event")

    new_round = Round(**round_in.model_dump())
    db.add(new_round)
    await db.commit()
    await db.refresh(new_round)
    return new_round

@router.get("/{event_id}", response_model=List[RoundSchema])
async def list_rounds(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Round).where(Round.event_id == event_id))
    return result.scalars().all()
