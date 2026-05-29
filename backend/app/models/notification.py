import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Enum,
    DateTime,
    ForeignKey,
    Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class NotificationType(str, enum.Enum):
    info = "info"
    alert = "alert"
    action_required = "action_required"


class Notification(Base):
    __tablename__ = "notifications"

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
    
    user_id = Column(
        UUID(as_uuid=True),
        nullable=False, # We keep this generic so it can refer to Participant, Judge, or Organizer IDs
        index=True
    )
    
    title = Column(
        String,
        nullable=False
    )
    
    message = Column(
        String,
        nullable=False
    )
    
    type = Column(
        Enum(NotificationType),
        default=NotificationType.info,
        nullable=False
    )
    
    is_read = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    
    action_link = Column(
        String,
        nullable=True
    )
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    event = relationship("Event", backref="notifications")
