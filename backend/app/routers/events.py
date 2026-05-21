from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.event import Event, EventStatus
from app.schemas.event import Event as EventSchema, EventCreate, EventUpdate

router = APIRouter()

@router.post("/create", response_model=EventSchema, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: EventCreate,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    # Enforce that organizers can only create events for themselves
    if str(event_in.organizer_id) != str(current_user.id) and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not allowed to create events for other organizers")

    new_event = Event(**event_in.model_dump())
    db.add(new_event)
    try:
        await db.commit()
        await db.refresh(new_event)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Event hash already exists or invalid data")
        
    return new_event

@router.get("", response_model=List[EventSchema])
async def list_events(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Organizers see their events, admins see all, participants/judges see active events
    query = select(Event).options(selectinload(Event.rounds))
    if current_user.role == UserRole.organizer:
        query = query.where(Event.organizer_id == current_user.id)
    elif current_user.role in [UserRole.participant, UserRole.judge]:
        query = query.where(Event.status == EventStatus.active)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{id}", response_model=EventSchema)
async def get_event(
    id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Event).options(selectinload(Event.rounds)).where(Event.id == id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    # Access checks
    if current_user.role == UserRole.organizer and event.organizer_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized to view this event")
        
    return event

@router.put("/{id}", response_model=EventSchema)
async def update_event(
    id: UUID,
    event_in: EventUpdate,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Event).where(Event.id == id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    if event.organizer_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized to update this event")
        
    update_data = event_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event, key, value)
        
    await db.commit()
    await db.refresh(event)
    return event

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    id: UUID,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Event).where(Event.id == id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    if event.organizer_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this event")
        
    await db.delete(event)
    await db.commit()
    return None
