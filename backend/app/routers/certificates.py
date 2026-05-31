from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.middleware.auth import require_role, get_current_user
from app.models.user import User, UserRole
from app.models.event import Event, Round
from app.models.participant import Participant
from app.models.submission import Submission
from app.models.email import EmailType
from app.services.certificate_service import generate_certificate_html, generate_certificate_data
from app.services.email_service import draft_bulk_emails, send_email, mark_email_as_sent, mark_email_as_failed
from pydantic import BaseModel

router = APIRouter()


class CertificateSendRequest(BaseModel):
    event_id: str
    achievement: str = "Participation"  # Participation, Winner, Finalist, etc.
    participant_ids: List[str] = None  # None = send to all participants


class CertificateSendResponse(BaseModel):
    total_participants: int
    certificates_generated: int
    emails_sent: int
    emails_failed: int


@router.post(
    "/certificates/send",
    response_model=CertificateSendResponse,
    status_code=status.HTTP_201_CREATED
)
async def send_certificates(
    req: CertificateSendRequest,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate and mail certificates to participants.
    
    Uses Groq LLM to generate personalized, professional certificates.
    """
    try:
        event_id = UUID(req.event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event_id format"
        )
    
    # Fetch event
    event_result = await db.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalars().first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    # Fetch participants
    if req.participant_ids:
        participant_uuids = [UUID(p_id) for p_id in req.participant_ids]
        query = select(Participant).where(
            Participant.event_id == event_id,
            Participant.id.in_(participant_uuids)
        )
    else:
        query = select(Participant).where(Participant.event_id == event_id)
    
    participants_result = await db.execute(query)
    participants = participants_result.scalars().all()
    
    if not participants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No participants found for this event"
        )
    
    # Fetch user emails for participants
    participant_user_ids = [p.user_id for p in participants]
    users_result = await db.execute(
        select(User).where(User.id.in_(participant_user_ids))
    )
    users_by_id = {u.id: u for u in users_result.scalars().all()}
    
    certificates_generated = 0
    emails_sent = 0
    emails_failed = 0
    recipients_data = []
    
    for participant in participants:
        user = users_by_id.get(participant.user_id)
        if not user or not user.email:
            continue
        
        try:
            participant_name = user.name or "Participant"
            
            # Generate certificate HTML using Groq
            cert_html = generate_certificate_html(
                participant_name=participant_name,
                event_name=event.name,
                achievement=req.achievement,
                date=datetime.now().strftime("%B %d, %Y")
            )
            
            # Generate certificate metadata
            cert_data = generate_certificate_data(
                participant_name=participant_name,
                event_name=event.name,
                achievement=req.achievement,
                date=datetime.now().strftime("%B %d, %Y")
            )
            
            certificates_generated += 1
            
            # Prepare email content
            subject = f"{req.achievement} Certificate - {event.name}"
            body_html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <p>Dear {participant_name},</p>
                    <p>Congratulations! {cert_data.get('congratulatory_message', '')}</p>
                    <p>Your official certificate has been generated and is attached to this email.</p>
                    <p>You can download it and use it for your records.</p>
                    <p style="margin-top: 30px;">Best regards,<br/>Team EKAM</p>
                </body>
            </html>
            """
            
            body_text = f"""
Dear {participant_name},

Congratulations! {cert_data.get('congratulatory_message', '')}

Your official certificate has been generated and is attached to this email.
You can download it and use it for your records.

Best regards,
Team EKAM
            """
            
            # Send email with certificate attachment
            cert_filename = f"certificate_{participant_name.replace(' ', '_')}.html"
            attachments = {cert_filename: cert_html.encode('utf-8')}
            
            email_sent = send_email(
                recipient_email=user.email,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                attachments=attachments
            )
            
            if email_sent:
                emails_sent += 1
            else:
                emails_failed += 1
            
            # Record in database
            recipients_data.append({
                "email": user.email,
                "name": participant_name,
                "achievement": req.achievement
            })
        
        except Exception as e:
            print(f"Error generating certificate for {user.email}: {e}")
            emails_failed += 1
            continue
    
    # Draft bulk emails for audit trail
    if recipients_data:
        await draft_bulk_emails(
            db=db,
            event_id=str(event_id),
            requested_by=current_user.id,
            email_type=EmailType.certificate,
            subject=f"{req.achievement} Certificate - {event.name}",
            body_html="<p>Certificates sent to participants</p>",
            body_text="Certificates sent to participants",
            recipients=[r["email"] for r in recipients_data],
            metadata={"achievement": req.achievement, "sent_certificates": len([r for r in recipients_data])}
        )
    
    return CertificateSendResponse(
        total_participants=len(participants),
        certificates_generated=certificates_generated,
        emails_sent=emails_sent,
        emails_failed=emails_failed
    )


@router.get("/certificates/{event_id}")
async def get_certificates_status(
    event_id: str,
    current_user: User = Depends(require_role([UserRole.organizer, UserRole.judge])),
    db: AsyncSession = Depends(get_db)
):
    """Get certificate status for an event."""
    try:
        event_id_uuid = UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event_id format"
        )
    
    result = await db.execute(
        select(Submission).join(
            Submission.__table__.c.round_id == Round.id
        ).where(Round.event_id == event_id_uuid)
    )
    
    return {
        "event_id": event_id,
        "status": "certificates_available",
        "message": "Certificates can be generated for participants"
    }
