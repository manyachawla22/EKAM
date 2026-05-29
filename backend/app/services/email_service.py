"""
EKAM Email Service

Drafts and sends emails.
Uses a draft-based model for batched emails (requires approval).
OTP/Magic links bypass approval for immediate delivery.
"""

from typing import List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.email import EmailDraft, EmailType, EmailStatus
from app.models.approval import RequestType

from app.services.approval_service import create_approval_request
import aiosmtplib
from email.message import EmailMessage
from app.core.config import settings


# =========================================================
# SENDING LOGIC (STUB)
# =========================================================

async def _send_email_stub(
    recipient: str,
    subject: str,
    body: str,
    email_type: str
) -> bool:
    """
    Real SMTP email sender using Brevo.
    """

    try:
        message = EmailMessage()

        message["From"] = settings.EMAIL_FROM
        message["To"] = recipient
        message["Subject"] = subject

        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )

        print("=" * 50)
        print(f"[{email_type.upper()}] EMAIL SENT")
        print(f"TO: {recipient}")
        print("=" * 50)

        return True

    except Exception as e:
        print("=" * 50)
        print("[EMAIL ERROR]")
        print(str(e))
        print("=" * 50)

        return False


async def send_email(
    db: AsyncSession,
    email_draft: EmailDraft
) -> bool:
    """Attempts to send a drafted email and updates its status."""
    
    success = await _send_email_stub(
        recipient=email_draft.recipient_email,
        subject=email_draft.subject,
        body=email_draft.body_text or email_draft.body_html or "",
        email_type=email_draft.email_type.value
    )
    
    if success:
        email_draft.status = EmailStatus.sent
        email_draft.sent_at = datetime.now(timezone.utc)
    else:
        email_draft.status = EmailStatus.failed
        
    await db.commit()
    return success


# =========================================================
# IMMEDIATE EMAILS (No Approval Required)
# =========================================================

async def send_otp_email(
    email: str,
    otp: str
):
    """Immediate delivery for OTP."""
    await _send_email_stub(
        recipient=email,
        subject="Your EKAM Login Code",
        body=f"Your OTP is: {otp}\nIt expires in 10 minutes.",
        email_type="otp"
    )


async def send_magic_link_email(
    email: str,
    link: str
):
    """Immediate delivery for Magic Links."""
    await _send_email_stub(
        recipient=email,
        subject="Your EKAM Magic Login Link",
        body=f"Click the following link to login: {link}\nIt expires in 48 hours.",
        email_type="magic_link"
    )


# =========================================================
# DRAFT-BASED EMAILS (Requires Approval)
# =========================================================

async def draft_email(
    db: AsyncSession,
    event_id: str,
    email_type: EmailType,
    recipient_email: str,
    subject: str,
    body_html: str,
    body_text: str | None = None,
    recipient_name: str | None = None,
    approval_id: str | None = None,
) -> EmailDraft:
    """Create a single email draft."""
    
    draft = EmailDraft(
        event_id=event_id,
        email_type=email_type,
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        status=EmailStatus.pending_approval if approval_id else EmailStatus.draft,
        approval_id=approval_id,
    )
    
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return draft


async def draft_bulk_emails(
    db: AsyncSession,
    event_id: str,
    requested_by: str,
    email_type: EmailType,
    subject: str,
    body_html: str,
    recipients: List[str],
    body_text: str | None = None,
):
    """
    Create an approval request, then create email drafts linked to it.
    """
    
    payload = {
        "email_type": email_type.value,
        "subject": subject,
        "recipient_count": len(recipients)
    }
    
    approval = await create_approval_request(
        db=db,
        event_id=event_id,
        request_type=RequestType.email_batch,
        payload=payload,
        requested_by=requested_by
    )
    
    drafts = []
    for recipient in recipients:
        draft = EmailDraft(
            event_id=event_id,
            email_type=email_type,
            recipient_email=recipient,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            status=EmailStatus.pending_approval,
            approval_id=approval.id
        )
        db.add(draft)
        drafts.append(draft)
        
    await db.commit()
    return approval, drafts


async def execute_approved_email_batch(
    db: AsyncSession,
    approval_id: str
):
    """
    Executed by the Approval Service when an email batch is approved.
    Fetches all linked drafts, marks them as approved, and sends them.
    """
    result = await db.execute(
        select(EmailDraft).where(
            EmailDraft.approval_id == approval_id,
            EmailDraft.status == EmailStatus.pending_approval
        )
    )
    drafts = result.scalars().all()
    
    sent_count = 0
    for draft in drafts:
        draft.status = EmailStatus.approved
        await db.commit() # commit status change before sending
        
        success = await send_email(db, draft)
        if success:
            sent_count += 1
            
    return sent_count


async def list_drafts(
    db: AsyncSession,
    event_id: str
) -> List[EmailDraft]:
    """List all email drafts for an event."""
    result = await db.execute(
        select(EmailDraft).where(
            EmailDraft.event_id == event_id
        ).order_by(EmailDraft.created_at.desc())
    )
    return list(result.scalars().all())