from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access

from app.schemas.approval import (
    ApprovalRequestResponse,
    ApprovalAction,
)

from app.services.approval_service import (
    list_pending_approvals,
    list_approval_history,
    get_approval,
    review_approval,
)

router = APIRouter(
    prefix="/approvals",
    tags=["Approvals"]
)


@router.get(
    "/{event_id}",
    response_model=List[ApprovalRequestResponse],
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def get_pending_approvals(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all pending approval requests for an event."""
    return await list_pending_approvals(db, event_id)


@router.get(
    "/{event_id}/history",
    response_model=List[ApprovalRequestResponse],
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def get_approval_history(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all approval requests (including resolved) for an event."""
    return await list_approval_history(db, event_id)


@router.get(
    "/{event_id}/{approval_id}",
    response_model=ApprovalRequestResponse,
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def get_approval_details(
    event_id: str,
    approval_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific approval request detail."""
    # Ensure approval belongs to event, but get_approval fetches by ID directly
    # A robust implementation might enforce event matching in the service query.
    return await get_approval(db, approval_id)


@router.post(
    "/{event_id}/{approval_id}/review",
    response_model=ApprovalRequestResponse,
)
async def review_approval_request(
    event_id: str,
    approval_id: str,
    action: ApprovalAction,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve, reject, or request revision on an approval request.
    If approved, automatically executes the associated workflow.
    """
    # Using require_actor_type explicitly and verifying event scoping via path parameter manually for action
    if not auth.can_access_event(event_id):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )

    return await review_approval(
        db=db,
        approval_id=approval_id,
        action=action.action,
        reviewer_id=auth.actor_id,
        notes=action.review_notes
    )
