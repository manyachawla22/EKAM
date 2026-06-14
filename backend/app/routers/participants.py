"""
EKAM Participants Router
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access

from app.models.participant import Participant as ParticipantModel
from app.models.event import Event as EventModel

from app.schemas.participant import (
    Participant,
    ParticipantCreate
)

from app.services.participant_service import (
    register_participant_service,
    list_participants_service
)
from app.services.csv_service import (
    parse_participant_csv,
    bulk_insert_participants,
    generate_participant_sample_csv,
)

router = APIRouter(
    prefix="/participants",
    tags=["Participants"]
)


@router.get(
    "/{event_id}/sample-csv",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def download_participant_sample_csv(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download a CSV template tailored to THIS event's registration fields (#3),
    so the organizer fills exactly what the event needs and the importer maps it."""
    event = (
        await db.execute(select(EventModel).where(EventModel.id == event_id))
    ).scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    csv_text = generate_participant_sample_csv(event)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="participants_sample.csv"'
        },
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

    result = await bulk_insert_participants(db, event_id, participants_data)
    inserted, skipped = result["inserted"], result["skipped"]

    if inserted > 0:
        message = f"Successfully imported {inserted} participant{'s' if inserted != 1 else ''}"
        if skipped:
            message += f" ({skipped} skipped — already added or duplicate)"
    elif skipped:
        message = f"No new participants added — {skipped} already exist for this event."
    else:
        message = "No valid rows found. Ensure your CSV has 'name' and 'email' column headers."

    return {"message": message, "count": inserted, "skipped": skipped}


@router.post(
    "/register",
    response_model=Participant,
    status_code=status.HTTP_201_CREATED,
    # Open to any authenticated actor:
    # - Organizers/admins register participants on their behalf
    # - Participants self-register for an event from the participant UI
    dependencies=[
        Depends(require_actor_type(["organizer", "participant"]))
    ],
)
async def register_participant(
    participant_in: ParticipantCreate,
    auth: AuthContext = Depends(
        require_actor_type(["organizer", "participant"])
    ),
    db: AsyncSession = Depends(get_db),
):
    """Register a single participant.

    Organizers can register anyone; participants can only register
    themselves (the body's email must match the JWT identity).
    """
    if auth.actor_type == "participant":
        # A participant can only self-register. The User entity carries the
        # authoritative email; reject if the body claims a different identity.
        user_email = getattr(auth.entity, "email", None)
        body_email = participant_in.email
        if user_email and body_email and user_email.lower() != body_email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Participants may only register themselves "
                    "(email must match the signed-in account)."
                ),
            )

        # Time gate: self-registration must fall inside the event's registration
        # window. Organizers (below) can still add people anytime, since they
        # manage the deadlines. No window configured → always open.
        event = (
            await db.execute(
                select(EventModel).where(EventModel.id == participant_in.event_id)
            )
        ).scalars().first()
        if event:
            from app.services.time_enforcement import registration_window_state

            reg_ok, reg_reason = registration_window_state(event)
            if not reg_ok:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=reg_reason,
                )
    else:
        # Organizers must own the event they're registering people into.
        if not auth.can_access_event(str(participant_in.event_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No event access",
            )

    return await register_participant_service(
        db,
        participant_in,
        auth.entity,
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