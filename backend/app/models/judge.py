import uuid

from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    ForeignKey,
    ARRAY,
    Boolean
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

from app.core.database import Base


class Judge(Base):
    __tablename__ = "judges"

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "email",
            name="uq_event_judge_email"
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

    expertise = Column(ARRAY(String), default=[])

    rating = Column(Float, default=5.0)

    # OTP Auth Fields
    is_verified = Column(Boolean, default=False)

    last_login = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    event = relationship("Event", back_populates="judges")

    assignments = relationship(
        "JudgeAssignment",
        back_populates="judge",
        cascade="all, delete-orphan"
    )

    evaluations = relationship(
        "Evaluation",
        back_populates="judge",
        cascade="all, delete-orphan"
    )


class JudgeAssignment(Base):
    __tablename__ = "judge_assignments"

    __table_args__ = (
        UniqueConstraint(
            "judge_id",
            "team_id",
            "round_id",
            name="uq_judge_team_round"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    judge_id = Column(
        UUID(as_uuid=True),
        ForeignKey("judges.id"),
        nullable=False
    )

    team_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teams.id"),
        nullable=False
    )

    round_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rounds.id"),
        nullable=False
    )

    assigned_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    judge = relationship("Judge", back_populates="assignments")

    team = relationship("Team", back_populates="judge_assignments")

    round = relationship("Round", back_populates="judge_assignments")