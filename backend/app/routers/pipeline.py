"""
EKAM Pipeline Router
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access, get_current_actor

from app.services.pipeline_service import propose_stage_transition, get_state, advance_pipeline
from pydantic import BaseModel

router = APIRouter(
    prefix="/pipeline",
    tags=["Pipeline"]
)

class StageTransitionRequest(BaseModel):
    target_stage: str
    cutoff_score: float


class AdvanceRequest(BaseModel):
    cutoff_score: float = 0.0


@router.get(
    "/{event_id}/state",
    dependencies=[Depends(require_event_access("event_id"))],
)
async def pipeline_state(
    event_id: str,
    auth: AuthContext = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db),
):
    """Dynamic per-round pipeline: ordered steps, current position, and whether
    the current step is ready to advance."""
    return await get_state(db, event_id)

@router.post(
    "/{event_id}/transition",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def transition_stage(
    event_id: str,
    data: StageTransitionRequest,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Propose a stage transition for teams meeting the cutoff score.
    Creates an ApprovalRequest.
    """
    approval = await propose_stage_transition(
        db=db,
        event_id=event_id,
        requested_by=auth.actor_id,
        target_stage=data.target_stage,
        cutoff_score=data.cutoff_score
    )
    
    return {
        "message": "Stage transition proposed.",
        "approval_id": str(approval.id)
    }


@router.post(
    "/{event_id}/advance",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def advance_pipeline_step(
    event_id: str,
    data: AdvanceRequest | None = None,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    """Directly advance the dynamic pipeline by one real step (no skipping).

    Used by the organizer's "Advance" control so progression follows the actual
    per-round pipeline instead of the coarse, hardcoded stage list.
    """
    return await advance_pipeline(
        db=db,
        event_id=event_id,
        cutoff_score=data.cutoff_score if data else 0.0,
    )
