import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Enum,
    DateTime,
    ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class EmailType(str, enum.Enum):
    otp = "otp"
    magic_link = "magic_link"
    invitation = "invitation"
    team_assignment = "team_assignment"
    stage_update = "stage_update"
    reminder = "reminder"
    result = "result"
    progression = "progression"


class EmailStatus(str, enum.Enum):
    draft = "draft"
    pending_approval = "pending_approval"
    approved = "approved"
    sent = "sent"
    failed = "failed"


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    email_type = Column(
        Enum(EmailType),
        nullable=False,
        index=True
    )
    
    recipient_email = Column(
        String,
        nullable=False,
        index=True
    )
    
    recipient_name = Column(
        String,
        nullable=True
    )
    
    subject = Column(
        String,
        nullable=False
    )
    
    body_html = Column(
        String,
        nullable=True
    )
    
    body_text = Column(
        String,
        nullable=True
    )
    
    status = Column(
        Enum(EmailStatus),
        default=EmailStatus.draft,
        nullable=False,
        index=True
    )
    
    approval_id = Column(
        UUID(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="SET NULL"),
        nullable=True
    )

    sent_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    event = relationship("Event", backref="email_drafts")
    approval_request = relationship("ApprovalRequest", backref="emails")
