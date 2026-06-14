import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Boolean
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

from app.core.database import Base


class TeamPreference(Base):
    __tablename__ = "team_preferences"
    __table_args__ = (
        UniqueConstraint("team_id", "participant_id", name="uq_team_participant_preference"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False)
    preferred_name = Column(String, nullable=False)
    preferred_theme_id = Column(UUID(as_uuid=True), ForeignKey("themes.id"), nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    team = relationship("Team", back_populates="preferences")
    participant = relationship("Participant")


class Team(Base):
    __tablename__ = "teams"

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "name",
            name="uq_event_team_name"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("events.id"),
        nullable=False
    )

    theme_id = Column(
        UUID(as_uuid=True),
        ForeignKey("themes.id"),
        nullable=True
    )

    name = Column(String, nullable=False)

    # Set when a team misses a submission deadline (or is otherwise removed for
    # cause). Disqualified teams are also added to EventPipeline.eliminated_team_ids
    # so the existing exclusion machinery keeps them out of later rounds and
    # leaderboards. Reversible via the round-window "reopen" path.
    disqualified = Column(Boolean, default=False, nullable=False)

    disqualified_reason = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    event = relationship("Event", back_populates="teams")

    theme = relationship("Theme", back_populates="teams")

    members = relationship(
        "TeamMember",
        back_populates="team",
        cascade="all, delete-orphan"
    )

    preferences = relationship(
        "TeamPreference",
        back_populates="team",
        cascade="all, delete-orphan"
    )

    submissions = relationship(
        "Submission",
        back_populates="team",
        cascade="all, delete-orphan"
    )

    judge_assignments = relationship(
        "JudgeAssignment",
        back_populates="team",
        cascade="all, delete-orphan"
    )


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "participant_id",
            name="uq_team_participant"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    team_id = Column(
        UUID(as_uuid=True),
        ForeignKey("teams.id"),
        nullable=False
    )

    participant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("participants.id"),
        nullable=False
    )

    is_leader = Column(Boolean, default=False)

    joined_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    team = relationship("Team", back_populates="members")

    participant = relationship(
        "Participant",
        back_populates="team_memberships"
    )
