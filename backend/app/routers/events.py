"""
EKAM Events Router
"""

from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_actor_type, get_current_actor, require_event_access
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
from app.services.winner_service import propose_winners, finalize_winners


class WinnerEntry(BaseModel):
    rank: int
    team_id: UUID
    team_name: Optional[str] = None
    score: Optional[float] = None
    prize: Optional[str] = None


class WinnersConfirm(BaseModel):
    winners: List[WinnerEntry]

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


@router.get(
    "/{event_id}/winners/proposal",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id")),
    ],
)
async def get_winners_proposal(
    event_id: UUID,
    top_n: int = 3,
    db: AsyncSession = Depends(get_db),
):
    """Top-N teams (by score) proposed as winners for the organizer to confirm."""
    return await propose_winners(db, event_id, top_n=top_n)


@router.post(
    "/{event_id}/winners",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id")),
    ],
)
async def confirm_winners(
    event_id: UUID,
    body: WinnersConfirm,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    """Confirm winners → send announcement + prize/next-steps + certificates."""
    winners = [w.model_dump() for w in body.winners]
    for w in winners:
        w["team_id"] = str(w["team_id"])
    return await finalize_winners(db, event_id, winners, requested_by=str(auth.actor_id))


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
    import traceback

    if not auth.can_access_event(str(event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )

    try:
        return await update_event_service(
            db,
            event_id,
            event_in,
            auth.entity,
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"update_event failed: {type(e).__name__}: {e}",
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