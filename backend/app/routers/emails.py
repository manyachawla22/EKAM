"""
EKAM Emails Router

Draft and batch email operations for Organizers.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access

from app.schemas.email import (
    EmailDraftResponse,
    EmailDraftCreate,
    BulkEmailDraftRequest
)

from app.services.email_service import (
    draft_email,
    draft_bulk_emails,
    list_drafts,
    send_email,
    resend_failed_emails
)
from app.models.email import EmailDraft
from sqlalchemy.future import select

router = APIRouter(
    prefix="/emails",
    tags=["Emails"]
)


@router.get(
    "/{event_id}/drafts",
    response_model=List[EmailDraftResponse],
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def get_email_drafts(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all email drafts for a given event."""
    return await list_drafts(db, event_id)


@router.post(
    "/{event_id}/resend-failed",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def resend_failed(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retry all previously-failed email drafts for this event (throttled)."""
    return await resend_failed_emails(db, event_id)


@router.post(
    "/draft",
    response_model=EmailDraftResponse,
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def create_single_draft(
    data: EmailDraftCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Create a single email draft (doesn't send it immediately)."""
    if not auth.can_access_event(str(data.event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )
        
    return await draft_email(
        db=db,
        event_id=str(data.event_id),
        email_type=data.email_type,
        recipient_email=data.recipient_email,
        subject=data.subject,
        body_html=data.body_html,
        body_text=data.body_text,
        recipient_name=data.recipient_name
    )


@router.post(
    "/bulk-draft",
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def create_bulk_drafts(
    data: BulkEmailDraftRequest,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a bulk email batch.
    Creates an ApprovalRequest and links the drafts to it.
    The emails will be sent when the ApprovalRequest is approved.
    """
    if not auth.can_access_event(str(data.event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )
        
    approval, drafts = await draft_bulk_emails(
        db=db,
        event_id=str(data.event_id),
        requested_by=auth.actor_id,
        email_type=data.email_type,
        subject=data.subject,
        body_html=data.body_html,
        body_text=data.body_text,
        recipients=data.recipients
    )
    
    return {
        "message": f"Created {len(drafts)} drafts and pending ApprovalRequest.",
        "approval_id": str(approval.id),
        "draft_count": len(drafts)
    }


@router.post(
    "/{email_id}/send",
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def send_individual_draft(
    email_id: str,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Send an individual drafted email immediately.
    Cannot be used for emails that are part of a pending batch approval.
    """
    result = await db.execute(select(EmailDraft).where(EmailDraft.id == email_id))
    draft = result.scalars().first()
    
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )
        
    if not auth.can_access_event(str(draft.event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )
        
    if draft.approval_id:
        from app.models.approval import ApprovalRequest, ApprovalStatus
        appr_res = await db.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == draft.approval_id)
        )
        approval = appr_res.scalars().first()
        if approval and approval.status == ApprovalStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send draft that is part of a pending bulk approval. Approve the batch instead."
            )
            
    success = await send_email(db, draft)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email"
        )
        
    return {"message": "Email sent successfully"}
