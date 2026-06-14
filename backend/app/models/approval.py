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
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class RequestType(str, enum.Enum):
    team_formation = "team_formation"
    judge_assignment = "judge_assignment"
    email_batch = "email_batch"
    leaderboard_publish = "leaderboard_publish"
    stage_transition = "stage_transition"
    progression = "progression"
    # Publishing/editing the public registration form (Task 6). The executor
    # writes the approved field set onto Event.registration_form_fields.
    registration_form = "registration_form"
    # Publishing an AI-designed event (gated deploy). On approval the executor
    # flips the draft event to active and materializes rounds/judges/rubric.
    event_deploy = "event_deploy"
    # Reviewing a flagged scoring anomaly (#2). The organizer decides whether the
    # anomaly is worth considering BEFORE the judge is notified. On approval the
    # executor emails the judge + organizer and reveals it on the judge's page;
    # on rejection it's dismissed and never shown to the judge.
    anomaly_review = "anomaly_review"


class ApprovalStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    revised = "revised"


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

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
    
    request_type = Column(
        Enum(RequestType),
        nullable=False,
        index=True
    )
    
    status = Column(
        Enum(ApprovalStatus),
        default=ApprovalStatus.pending,
        nullable=False,
        index=True
    )
    
    payload = Column(
        JSONB,
        nullable=False
    )
    
    requested_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    review_notes = Column(
        String,
        nullable=True
    )

    requested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    event = relationship("Event", backref="approval_requests")
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
