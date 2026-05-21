import uuid
import enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class EventStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    archived = "archived"

class EventStage(str, enum.Enum):
    draft = "Draft"
    registration_open = "Registration Open"
    registration_closed = "Registration Closed"
    oa_round = "OA Round"
    team_formation = "Team Formation"
    submission_round = "Submission Round"
    evaluation_round = "Evaluation Round"
    results_generated = "Results Generated"
    completed = "Event Completed"

class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hash = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(Enum(EventStatus), default=EventStatus.draft)
    stage = Column(Enum(EventStage), default=EventStage.draft)
    max_participants = Column(Integer, default=0)
    organizer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    rounds = relationship("Round", back_populates="event", cascade="all, delete-orphan")


class RoundStatus(str, enum.Enum):
    upcoming = "upcoming"
    active = "active"
    completed = "completed"

class Round(Base):
    __tablename__ = "rounds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    name = Column(String, nullable=False)
    status = Column(Enum(RoundStatus), default=RoundStatus.upcoming)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    event = relationship("Event", back_populates="rounds")
