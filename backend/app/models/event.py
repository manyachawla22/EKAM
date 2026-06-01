import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Enum,
    Text
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class EventStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    archived = "archived"


class TeamFormationType(str, enum.Enum):
    platform_generated = "platform_generated"
    preformed = "preformed"


class EventStage(str, enum.Enum):
    registration = "registration"
    team_formation = "team_formation"
    submission = "submission"
    evaluation = "evaluation"
    completed = "completed"


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    organizer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )

    name = Column(String, nullable=False)

    hash = Column(String, unique=True, index=True, nullable=False)

    description = Column(Text, nullable=True)

    type = Column(String, nullable=False)

    status = Column(
        Enum(EventStatus),
        default=EventStatus.draft
    )

    stage = Column(
        Enum(EventStage),
        default=EventStage.registration
    )

    team_formation_type = Column(
        Enum(TeamFormationType),
        default=TeamFormationType.platform_generated
    )

    min_team_size = Column(Integer, default=1)

    max_team_size = Column(Integer, default=4)

    max_participants = Column(Integer, default=0)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

    # Relationships
    organizer = relationship("User", back_populates="events")

    rounds = relationship(
        "Round",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    themes = relationship(
        "Theme",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    participants = relationship(
        "Participant",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    judges = relationship(
        "Judge",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    teams = relationship(
        "Team",
        back_populates="event",
        cascade="all, delete-orphan"
    )


class RoundStatus(str, enum.Enum):
    upcoming = "upcoming"
    active = "active"
    completed = "completed"


class Round(Base):
    __tablename__ = "rounds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id"),
        nullable=False
    )

    name = Column(String, nullable=False)

    description = Column(Text, nullable=True)

    status = Column(
        Enum(RoundStatus),
        default=RoundStatus.upcoming
    )

    start_date = Column(DateTime(timezone=True), nullable=True)

    end_date = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    event = relationship("Event", back_populates="rounds")

    submissions = relationship(
        "Submission",
        back_populates="round",
        cascade="all, delete-orphan"
    )

    judge_assignments = relationship(
        "JudgeAssignment",
        back_populates="round",
        cascade="all, delete-orphan"
    )