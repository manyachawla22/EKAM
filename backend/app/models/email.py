import uuid
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class EmailType(str, enum.Enum):
    invitation = "invitation"
    team_assignment = "team_assignment"
    stage_update = "stage_update"
    magic_link = "magic_link"
    result = "result"
    progression = "progression"
    certificate = "certificate"


class Email(Base):
    __tablename__ = "emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    
    recipient_email = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=False)
    body_text = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    
    email_type = Column(Enum(EmailType), nullable=False)
    status = Column(String, default="drafted")  # drafted, sent, failed, bounced
    
    metadata = Column(JSONB, default={})  # stores recipient_name, team_name, etc.
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
