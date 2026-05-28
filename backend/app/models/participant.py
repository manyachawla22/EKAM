import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Enum,
    Float,
    Boolean,
    ARRAY
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

from app.core.database import Base


class RegistrationStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    rejected = "rejected"


class Participant(Base):
    __tablename__ = "participants"

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "email",
            name="uq_event_participant_email"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id"),
        nullable=False
    )

    name = Column(String, nullable=False)

    email = Column(String, nullable=False)

    institution = Column(String, nullable=True)

    phone = Column(String, nullable=True)

    gender = Column(String, nullable=True)

    age = Column(Integer, nullable=True)

    skills = Column(ARRAY(String), default=[])

    ats_score = Column(Float, nullable=True)

    status = Column(
        Enum(RegistrationStatus),
        default=RegistrationStatus.pending
    )

    # OTP Auth Fields
    otp_code = Column(String, nullable=True)

    otp_expiry = Column(DateTime(timezone=True), nullable=True)

    is_verified = Column(Boolean, default=False)

    last_login = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    event = relationship("Event", back_populates="participants")

    team_memberships = relationship(
        "TeamMember",
        back_populates="participant",
        cascade="all, delete-orphan"
    )
