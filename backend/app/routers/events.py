"""
EKAM Events Router
"""

from uuid import UUID
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.event import Event as EventModel

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


class RegistrationWindowUpdate(BaseModel):
    # Pass either/both; null clears that bound (making it unbounded on that side).
    registration_opens_at: Optional[datetime] = None
    registration_closes_at: Optional[datetime] = None


class RegistrationFormField(BaseModel):
    field_id: str
    label: str
    type: str = "text"  # text|email|tel|url|select|textarea|number|date
    required: bool = False
    options: Optional[List[str]] = None
    unique_per_event: Optional[bool] = None


class RegistrationFormProposal(BaseModel):
    """Organizer's manual registration-form edit. Publishing it is approval-gated
    (creates a `registration_form` ApprovalRequest) — same human-in-the-loop gate
    the rest of the app uses."""
    fields: List[RegistrationFormField]
    participants_model: Optional[str] = None  # "individual" | "team"
    individual_registration_allowed: Optional[bool] = None


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


@router.patch(
    "/{event_id}/registration-window",
    response_model=Event,
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id")),
    ],
)
async def update_registration_window(
    event_id: UUID,
    body: RegistrationWindowUpdate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    """Organizer sets/postpones the event's registration window. Times should be
    sent as ISO8601 (UTC or with an offset); they're stored as-is (tz-aware)."""
    event = (
        await db.execute(select(EventModel).where(EventModel.id == event_id))
    ).scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    fields = body.model_dump(exclude_unset=True)
    if "registration_opens_at" in fields:
        event.registration_opens_at = fields["registration_opens_at"]
    if "registration_closes_at" in fields:
        event.registration_closes_at = fields["registration_closes_at"]

    await db.commit()
    await db.refresh(event)
    return event


@router.post(
    "/{event_id}/registration-form",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id")),
    ],
)
async def propose_registration_form(
    event_id: UUID,
    body: RegistrationFormProposal,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    """Propose a public registration form (manual editor). Creates a pending
    `registration_form` approval; the form goes live only once approved from the
    Approvals panel. Returns the created approval request."""
    from app.models.approval import RequestType
    from app.services.approval_service import create_approval_request

    event = (
        await db.execute(select(EventModel).where(EventModel.id == event_id))
    ).scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    payload = body.model_dump(exclude_none=True)
    approval = await create_approval_request(
        db,
        event_id=str(event_id),
        request_type=RequestType.registration_form,
        payload=payload,
        requested_by=str(auth.actor_id),
    )
    return {
        "approval_id": str(approval.id),
        "status": approval.status.value,
        "message": "Registration form submitted for approval.",
    }


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


@router.get("/{event_id}/features")
async def get_event_features(
    event_id: UUID,
    auth: AuthContext = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db),
):
    """Per-event feature flags derived from the event + its blueprint, so the UI
    only shows what an event actually uses (e.g. the Bracket tab only for
    tournaments). Cheap; safe for any actor with event access."""
    if auth.actor_type != "organizer" and not auth.can_access_event(str(event_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No event access")

    event = (await db.execute(select(EventModel).where(EventModel.id == event_id))).scalars().first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    bp = event.blueprint or {}
    stages = bp.get("stages") or []
    types = [(s.get("type") or "").lower() for s in stages]
    is_team = (event.participants_model or "individual") == "team"

    # A round is live-judged when an evaluation has no submission since the previous
    # evaluation (mirrors the generator's live_judging derivation).
    has_live = False
    pending_sub = False
    for t in types:
        if t == "submission":
            pending_sub = True
        elif t == "evaluation":
            if not pending_sub:
                has_live = True
            pending_sub = False

    return {
        "has_bracket": "bracket" in types,        # show the Bracket tab
        "has_teams": is_team,                       # Teams tab meaningful for team events
        "has_live_rounds": has_live,               # any live-judged round
        "blueprint_driven": bool(event.blueprint), # Event OS vs legacy hackathon
        "format_label": bp.get("format_label"),
    }


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