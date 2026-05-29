"""
EKAM Events Router
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_actor_type, get_current_actor
from app.core.auth_context import AuthContext

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
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def create_event(
    event_in: EventCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new event."""
    return await create_event_service(
        db,
        event_in,
        auth.entity
    )


@router.get("", response_model=List[Event])
async def list_events(
    auth: AuthContext = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db)
):
    """List events visible to the current actor."""
    return await list_events_service(
        db,
        auth.entity
    )


@router.get("/{event_id}", response_model=Event)
async def get_event(
    event_id: UUID,
    auth: AuthContext = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific event."""
    # Add check for event access
    if auth.actor_type != "organizer" and not auth.can_access_event(str(event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )
        
    return await get_event_service(
        db,
        event_id,
        auth.entity
    )


@router.put(
    "/{event_id}",
    response_model=Event,
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def update_event(
    event_id: UUID,
    event_in: EventUpdate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Update an event."""
    if not auth.can_access_event(str(event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )
        
    return await update_event_service(
        db,
        event_id,
        event_in,
        auth.entity
    )


@router.delete(
    "/{event_id}",
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def delete_event(
    event_id: UUID,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Delete an event."""
    if not auth.can_access_event(str(event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )
        
    return await delete_event_service(
        db,
        event_id,
        auth.entity
    )