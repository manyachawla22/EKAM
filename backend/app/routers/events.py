from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import (
    get_current_user,
    require_role
)

from app.models.user import User, UserRole

from app.schemas.event import (
    Event,
    EventCreate,
    EventUpdate
)

from app.services.event_service import (
    create_event_service,
    list_events_service,
    get_event_service,
    update_event_service,
    delete_event_service
)

router = APIRouter(
    prefix="/events",
    tags=["Events"]
)


@router.post(
    "/create",
    response_model=Event,
    status_code=status.HTTP_201_CREATED
)
async def create_event(
    event_in: EventCreate,
    current_user: User = Depends(
        require_role([UserRole.organizer, UserRole.admin])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await create_event_service(
        db,
        event_in,
        current_user
    )


@router.get("", response_model=List[Event])
async def list_events(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await list_events_service(
        db,
        current_user
    )


@router.get("/{event_id}", response_model=Event)
async def get_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_event_service(
        db,
        event_id,
        current_user
    )


@router.put("/{event_id}", response_model=Event)
async def update_event(
    event_id: UUID,
    event_in: EventUpdate,
    current_user: User = Depends(
        require_role([UserRole.organizer, UserRole.admin])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await update_event_service(
        db,
        event_id,
        event_in,
        current_user
    )


@router.delete("/{event_id}")
async def delete_event(
    event_id: UUID,
    current_user: User = Depends(
        require_role([UserRole.organizer, UserRole.admin])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await delete_event_service(
        db,
        event_id,
        current_user
    )