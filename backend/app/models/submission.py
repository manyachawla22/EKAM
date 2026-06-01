import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum,
    ARRAY
)

from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    reviewed = "reviewed"
    flagged = "flagged"
    finalised = "finalised"


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

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

    attachments = Column(ARRAY(String), default=[])

    status = Column(
        Enum(SubmissionStatus),
        default=SubmissionStatus.pending
    )

    final_score = Column(Float, nullable=True)

    panel_average = Column(Float, nullable=True)

    submitted_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    # Relationships
    team = relationship("Team", back_populates="submissions")

    round = relationship("Round", back_populates="submissions")

    evaluations = relationship(
        "Evaluation",
        back_populates="submission",
        cascade="all, delete-orphan"
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    submission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id"),
        nullable=False
    )

    judge_id = Column(
        UUID(as_uuid=True),
        ForeignKey("judges.id"),
        nullable=False
    )

    # Rubric Based Scoring
    rubric_scores = Column(JSONB, default={})

    total_score = Column(Float, nullable=False)

    feedback = Column(String, nullable=True)

    evaluated_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    submission = relationship(
        "Submission",
        back_populates="evaluations"
    )

    judge = relationship(
        "Judge",
        back_populates="evaluations"
    )