import uuid
import enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Enum,
    Text,
    Boolean
)

from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    results = "results"
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

    # Registration window (UTC). When set, the public registration endpoint
    # rejects self-registrations outside [opens_at, closes_at]. Nullable so
    # events without a configured window behave as before (always open).
    registration_opens_at = Column(DateTime(timezone=True), nullable=True)

    registration_closes_at = Column(DateTime(timezone=True), nullable=True)

    # ── Public registration page (Task 6) ───────────────────────────────────
    # The organizer-defined registration form. A list of field specs, e.g.
    # [{"field_id","label","type","required","options?","unique_per_event?"}].
    # Authored via the AI chat or the manual editor; the manual editor's edits
    # go live only after the registration_form ApprovalRequest is approved.
    registration_form_fields = Column(JSONB, nullable=True)

    # "individual" | "team" — drives the public registration flow shape.
    participants_model = Column(String, default="individual")

    # Whether a single person may register on their own (vs. only via a team).
    individual_registration_allowed = Column(Boolean, default=True)

    # Eligibility spec mirrored from the AI config (open_to, colleges, years…).
    # Advisory at the public edge — hard gates are window/capacity/uniqueness.
    eligibility = Column(JSONB, nullable=True)

    # Task 3 (Event OS): the approved Universal Event Blueprint that drives a
    # generic (non-hackathon) pipeline. NULL ⇒ legacy/hackathon event → build_steps
    # falls back to the hardcoded default (backward-compatible). Frozen after the
    # generator runs (edits happen pre-deploy on the review screen).
    blueprint = Column(JSONB, nullable=True)

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

    # Single source of truth for this round's advancement cutoff (#13). It is set
    # only when the advancement is executed (the approval is the only editor);
    # leaderboard / pipeline / approvals views read it read-only. Null until then.
    cutoff_score = Column(Float, nullable=True)

    # Task 3 (automated scoring): "human" (judges score via rubric) or "auto"
    # (scores ingested from an autograder/scoreboard → submission.final_score, no
    # judge assignment). Set by the generator from the blueprint's evaluation
    # stage scoring.method. "human" preserves all existing behaviour.
    scoring_mode = Column(String, default="human", server_default="human", nullable=False)

    # Task 3 (blind review): when True, reviewer-facing views hide the team/author
    # identity (shown as "Submission #…"). Set by the generator from a blueprint
    # evaluation stage's behaviors ["anonymous_review"]. False preserves behaviour.
    anonymous = Column(Boolean, default=False, server_default="false", nullable=False)

    # Task 3 (live rounds) — a feature flag, OFF by default. When False (default)
    # the round runs the normal flow: participants upload a submission, then judges
    # grade it. When True the round is LIVE-JUDGED: there is NO participant
    # submission step — a referee/judge scores performances, matches, debates,
    # quizzes, or pitches in real time. The pipeline then auto-creates a placeholder
    # Submission per active team so the team-keyed evaluation/leaderboard machinery
    # still works. Set by the generator: True when the blueprint round-group has an
    # evaluation but NO submission stage.
    live_judging = Column(Boolean, default=False, server_default="false", nullable=False)

    # Task 3 (quiz/question-bank, feature #8) — a feature flag, OFF by default. When
    # True the round draws from a per-round question bank (`questions` table): each
    # team gets a generated QuestionPaper (a subset of `questions_per_paper`
    # questions) shown on their dashboard; they upload one answer file; the judge
    # grades per-question (or the AI auto-checks against each question's answer).
    is_quiz = Column(Boolean, default=False, server_default="false", nullable=False)
    questions_per_paper = Column(Integer, default=0, server_default="0", nullable=False)

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