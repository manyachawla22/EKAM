from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.approval import ApprovalRequest, ApprovalStatus, RequestType


async def create_approval_request(
    db: AsyncSession,
    event_id: str,
    request_type: RequestType,
    payload: dict,
    requested_by: str,
) -> ApprovalRequest:
    """Create a new approval request in the pending state."""
    
    approval = ApprovalRequest(
        event_id=event_id,
        request_type=request_type,
        payload=payload,
        requested_by=requested_by,
        status=ApprovalStatus.pending
    )
    
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    return approval


async def list_pending_approvals(
    db: AsyncSession,
    event_id: str
) -> List[ApprovalRequest]:
    """List all pending approval requests for an event."""
    
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.event_id == event_id,
            ApprovalRequest.status == ApprovalStatus.pending
        ).order_by(ApprovalRequest.requested_at.desc())
    )
    
    return list(result.scalars().all())


async def list_approval_history(
    db: AsyncSession,
    event_id: str
) -> List[ApprovalRequest]:
    """List all approval requests for an event (including resolved)."""
    
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.event_id == event_id
        ).order_by(ApprovalRequest.requested_at.desc())
    )
    
    return list(result.scalars().all())


async def get_approval(
    db: AsyncSession,
    approval_id: str
) -> ApprovalRequest:
    """Get a specific approval request."""
    
    result = await db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id
        )
    )
    approval = result.scalars().first()
    
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found"
        )
        
    return approval


async def review_approval(
    db: AsyncSession,
    approval_id: str,
    action: ApprovalStatus,
    reviewer_id: str,
    notes: str | None = None
) -> ApprovalRequest:
    """Approve, reject, or request revision on an approval request."""
    
    if action not in [ApprovalStatus.approved, ApprovalStatus.rejected, ApprovalStatus.revised]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be approved, rejected, or revised."
        )
        
    approval = await get_approval(db, approval_id)
    
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot review request that is already {approval.status.value}"
        )
        
    approval.status = action
    approval.reviewed_by = reviewer_id
    approval.review_notes = notes
    approval.reviewed_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(approval)
    
    if action == ApprovalStatus.approved:
        await execute_approved_action(db, approval)
        
    return approval


async def execute_approved_action(
    db: AsyncSession,
    approval: ApprovalRequest
):
    """
    Dispatch the payload to the appropriate service for execution.
    This will be fully wired up in Phase 4 (CP-SAT), Phase 5 (Emails), etc.
    """
    
    # Wire up the actual execution functions for Phase 4
    if approval.request_type == RequestType.team_formation:
        from app.services.assignment_service import execute_team_formation
        await execute_team_formation(db, approval.payload)
        
    elif approval.request_type == RequestType.judge_assignment:
        from app.services.assignment_service import execute_judge_assignment
        await execute_judge_assignment(db, approval.payload)
        
    elif approval.request_type == RequestType.email_batch:
        # from app.services.email_service import execute_approved_email_batch
        # await execute_approved_email_batch(db, str(approval.id))
        pass
        
    elif approval.request_type == RequestType.leaderboard_publish:
        # publish leaderboard
        pass
        
    elif approval.request_type == RequestType.stage_transition:
        from app.services.pipeline_service import execute_stage_transition
        await execute_stage_transition(db, approval.payload)
        
    elif approval.request_type == RequestType.progression:
        # execute progression
        pass
        
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unknown request type {approval.request_type}"
        )
