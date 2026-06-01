from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

from app.models.email import EmailType, EmailStatus


class EmailDraftBase(BaseModel):
    event_id: UUID
    email_type: EmailType
    recipient_email: EmailStr
    recipient_name: Optional[str] = None
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None


class EmailDraftCreate(EmailDraftBase):
    pass


class EmailDraftResponse(EmailDraftBase):
    id: UUID
    status: EmailStatus
    approval_id: Optional[UUID] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BulkEmailDraftRequest(BaseModel):
    event_id: UUID
    email_type: EmailType
    subject: str
    body_html: str
    body_text: Optional[str] = None
    recipients: list[EmailStr]
