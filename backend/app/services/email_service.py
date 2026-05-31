import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List, Dict, Any, Optional

from app.models.email import Email, EmailType
from app.core.config import settings


async def draft_bulk_emails(
    db: AsyncSession,
    event_id: str,
    requested_by: str,
    email_type: EmailType,
    subject: str,
    body_html: str,
    body_text: str,
    recipients: List[str],
    metadata: Optional[Dict[str, Any]] = None
) -> List[Email]:
    """
    Create email records in the database (drafts) for later sending.
    
    Args:
        db: Database session
        event_id: Event UUID
        requested_by: User who requested the email
        email_type: Type of email (invitation, certificate, etc.)
        subject: Email subject
        body_html: HTML body
        body_text: Plain text body
        recipients: List of recipient email addresses
        metadata: Additional metadata for each email
    
    Returns:
        List of created Email records
    """
    emails = []
    
    for recipient in recipients:
        email = Email(
            event_id=UUID(event_id),
            recipient_email=recipient,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            email_type=email_type,
            status="drafted",
            metadata=metadata or {}
        )
        emails.append(email)
        db.add(email)
    
    await db.commit()
    return emails


def send_email(
    recipient_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None,
    attachments: Optional[Dict[str, bytes]] = None
) -> bool:
    """
    Send an email using SMTP.
    
    Args:
        recipient_email: Recipient email address
        subject: Email subject
        body_html: HTML body
        body_text: Plain text fallback
        attachments: Dict of {filename: file_bytes}
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            raise RuntimeError("SMTP credentials not configured")
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SENDER_NAME} <{settings.SENDER_EMAIL}>"
        msg["To"] = recipient_email
        
        # Attach plain text and HTML
        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))
        
        # Attach files if provided
        if attachments:
            from email.mime.base import MIMEBase
            from email import encoders
            
            for filename, file_bytes in attachments.items():
                part = MIMEBase("application", "octet-stream")
                part.set_payload(file_bytes)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename= {filename}")
                msg.attach(part)
        
        # Send email
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Error sending email to {recipient_email}: {e}")
        return False


async def mark_email_as_sent(db: AsyncSession, email_id: UUID) -> None:
    """Mark an email record as sent."""
    from sqlalchemy.future import select
    from datetime import datetime, timezone
    
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalars().first()
    
    if email:
        email.status = "sent"
        email.sent_at = datetime.now(timezone.utc)
        await db.commit()


async def mark_email_as_failed(db: AsyncSession, email_id: UUID, error_message: str) -> None:
    """Mark an email record as failed."""
    from sqlalchemy.future import select
    
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalars().first()
    
    if email:
        email.status = "failed"
        email.error_message = error_message
        await db.commit()
