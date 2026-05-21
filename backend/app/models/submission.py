import uuid
import enum
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum, ARRAY
from sqlalchemy.dialects.postgresql import UUID
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
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    round_id = Column(UUID(as_uuid=True), ForeignKey("rounds.id"), nullable=False)
    
    attachments = Column(ARRAY(String), default=[])
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.pending)
    score = Column(Float, nullable=True)
    panel_avg = Column(Float, nullable=True)
    feedback = Column(String, nullable=True)
    
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id"), nullable=False)
    judge_id = Column(UUID(as_uuid=True), ForeignKey("judges.id"), nullable=False)
    
    score = Column(Float, nullable=False)
    feedback = Column(String, nullable=True)
    
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
