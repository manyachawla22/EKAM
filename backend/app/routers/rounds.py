"""
EKAM Rounds Router
"""

from uuid import UUID
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db

from app.middleware.auth import require_actor_type, require_event_access
from app.core.auth_context import AuthContext

from app.models.event import Round as RoundModel
from app.models.pipeline import EventPipeline
from app.models.team import Team

from app.schemas.round import (
    Round,
    RoundCreate
)

from app.services.round_service import (
    create_round_service,
    list_rounds_service,
    delete_round_service,
)


class RoundWindowUpdate(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    # When extending a passed deadline, set reopen=True to also un-disqualify
    # teams that were disqualified *for this round* (and let them back into the
    # pipeline). Off by default — we never silently resurrect teams.
    reopen: bool = False


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


@router.patch(
    "/{event_id}/{round_id}/window",
    response_model=Round,
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id")),
    ],
)
async def update_round_window(
    event_id: UUID,
    round_id: UUID,
    body: RoundWindowUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Organizer sets/postpones a round's submission window. With reopen=True,
    also un-disqualifies teams that were disqualified for missing THIS round's
    deadline and removes them from the pipeline's eliminated set."""
    round_obj = (
        await db.execute(
            select(RoundModel).where(
                RoundModel.id == round_id, RoundModel.event_id == event_id
            )
        )
    ).scalars().first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")

    fields = body.model_dump(exclude_unset=True)
    if "start_date" in fields:
        round_obj.start_date = fields["start_date"]
    if "end_date" in fields:
        round_obj.end_date = fields["end_date"]

    if body.reopen:
        reason = f"Missed submission deadline for {round_obj.name}"
        dq_teams = (
            await db.execute(
                select(Team).where(
                    Team.event_id == event_id,
                    Team.disqualified == True,  # noqa: E712
                    Team.disqualified_reason == reason,
                )
            )
        ).scalars().all()
        if dq_teams:
            pipeline = (
                await db.execute(
                    select(EventPipeline).where(EventPipeline.event_id == event_id)
                )
            ).scalars().first()
            eliminated = list((pipeline.data or {}).get("eliminated_team_ids", [])) if pipeline else []
            restored_ids = {str(t.id) for t in dq_teams}
            for t in dq_teams:
                t.disqualified = False
                t.disqualified_reason = None
            if pipeline:
                pipeline.data = {
                    **(pipeline.data or {}),
                    "eliminated_team_ids": [e for e in eliminated if e not in restored_ids],
                }

    await db.commit()
    await db.refresh(round_obj)
    return round_obj


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