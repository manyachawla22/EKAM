"""
EKAM Participants Router
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access

from app.models.participant import Participant as ParticipantModel

from app.schemas.participant import (
    Participant,
    ParticipantCreate
)

from app.services.participant_service import (
    register_participant_service,
    list_participants_service
)
from app.services.csv_service import parse_participant_csv, bulk_insert_participants

router = APIRouter(
    prefix="/participants",
    tags=["Participants"]
)


@router.post(
    "/{event_id}/upload-csv",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def upload_participant_csv(
    event_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Bulk upload participants via CSV."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV"
        )
        
    content = await file.read()
    participants_data = parse_participant_csv(content)
    
    count = await bulk_insert_participants(db, event_id, participants_data)
    
    return {
        "message": f"Successfully imported {count} participants",
        "count": count
    }


@router.post(
    "/register",
    response_model=Participant,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def register_participant(
    participant_in: ParticipantCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Register a single participant manually."""
    if not auth.can_access_event(str(participant_in.event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )
        
    # auth.entity is the User for organizers
    return await register_participant_service(
        db,
        participant_in,
        auth.entity
    )


@router.get(
    "/{event_id}",
    response_model=List[Participant],
    dependencies=[
        Depends(require_actor_type(["organizer", "judge", "participant"])),
        Depends(require_event_access("event_id"))
    ]
)
async def list_participants(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all participants for an event."""
    return await list_participants_service(db, event_id)


@router.get(
    "/{event_id}/{participant_id}",
    response_model=Participant,
    dependencies=[
        Depends(require_actor_type(["organizer", "judge"])),
        Depends(require_event_access("event_id"))
    ]
)
async def get_participant(
    event_id: UUID,
    participant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ParticipantModel).where(
            ParticipantModel.id == participant_id,
            ParticipantModel.event_id == event_id
        )
    )
    participant = result.scalars().first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    return participant


@router.delete(
    "/{event_id}/{participant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def delete_participant(
    event_id: UUID,
    participant_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ParticipantModel).where(
            ParticipantModel.id == participant_id,
            ParticipantModel.event_id == event_id
        )
    )
    participant = result.scalars().first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
        
    await db.delete(participant)
    await db.commit()