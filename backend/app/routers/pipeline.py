"""
EKAM Pipeline Router
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access

from app.services.pipeline_service import propose_stage_transition
from pydantic import BaseModel

router = APIRouter(
    prefix="/pipeline",
    tags=["Pipeline"]
)

class StageTransitionRequest(BaseModel):
    target_stage: str
    cutoff_score: float

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
