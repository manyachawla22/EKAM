"""
EKAM Pipeline Service

Handles stage transitions and progression logic for teams.
Integrates with the Approval Workflow.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.approval import RequestType
from app.models.team import Team
from app.services.approval_service import create_approval_request


async def propose_stage_transition(
    db: AsyncSession,
    event_id: str,
    requested_by: str,
    target_stage: str,
    cutoff_score: float
):
    """
    Analyzes current scores and proposes a list of teams that should advance to the next stage.
    Creates an ApprovalRequest.
    """
    # In a real implementation, we would aggregate scores from LeaderboardService
    # and filter teams > cutoff_score.
    # For now, we stub this logic.
    
    result = await db.execute(select(Team))
    all_teams = result.scalars().all()
    
    # Stub: advance everyone
    advancing_teams = [{"team_id": str(t.id), "team_name": t.name, "score": 85.0} for t in all_teams]
    
    payload = {
        "target_stage": target_stage,
        "cutoff_score": cutoff_score,
        "advancing_teams": advancing_teams
    }
    
    approval = await create_approval_request(
        db=db,
        event_id=event_id,
        request_type=RequestType.stage_transition,
        payload=payload,
        requested_by=requested_by
    )
    
    return approval


async def execute_stage_transition(
    db: AsyncSession,
    payload: dict
):
    """
    Executed by the Approval Service once a stage transition is approved.
    """
    # Here we would update team statuses in the DB.
    pass
