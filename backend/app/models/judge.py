import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, ARRAY, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Judge(Base):
    __tablename__ = "judges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    expertise = Column(ARRAY(String), default=[])
    institution = Column(String, nullable=True)
    rating = Column(Float, default=5.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class JudgeAssignment(Base):
    __tablename__ = "judge_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    judge_id = Column(UUID(as_uuid=True), ForeignKey("judges.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    round_id = Column(UUID(as_uuid=True), ForeignKey("rounds.id"), nullable=True)
    
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
