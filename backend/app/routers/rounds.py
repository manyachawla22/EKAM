"""
EKAM Rounds Router
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_actor_type, require_event_access
from app.core.auth_context import AuthContext

from app.schemas.round import (
    Round,
    RoundCreate
)

from app.services.round_service import (
    create_round_service,
    list_rounds_service,
    delete_round_service,
)

router = APIRouter(
    prefix="/rounds",
    tags=["Rounds"]
)


@router.post(
    "/create",
    response_model=Round,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def create_round(
    round_in: RoundCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new round."""
    if not auth.can_access_event(str(round_in.event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )
        
    return await create_round_service(
        db,
        round_in,
        auth.entity
    )


@router.get(
    "/{event_id}",
    response_model=List[Round],
    dependencies=[
        Depends(require_actor_type(["organizer", "judge", "participant"])),
        Depends(require_event_access("event_id"))
    ]
)
async def list_rounds(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all rounds for an event."""
    return await list_rounds_service(db, event_id)


@router.delete(
    "/{event_id}/{round_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def delete_round(
    event_id: UUID,
    round_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a round."""
    await delete_round_service(db, event_id, round_id)