import uuid
import enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Float, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class RegistrationStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    waitlisted = "waitlisted"
    rejected = "rejected"

class Participant(Base):
    __tablename__ = "participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    
    institution = Column(String, nullable=True)
    skills = Column(ARRAY(String), default=[])
    gender = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    phone = Column(String, nullable=True)
    ats_score = Column(Float, nullable=True)
    
    status = Column(Enum(RegistrationStatus), default=RegistrationStatus.pending)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False)
    is_leader = Column(Integer, default=0)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
