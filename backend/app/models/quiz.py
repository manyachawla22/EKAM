"""
EKAM Quiz / Question-Bank models (Task 3, feature #8 from possible.md).

A quiz/coding round draws from a per-round QUESTION BANK (parsed from the
organizer's .md/.csv). Each team gets a generated QuestionPaper — a subset of the
bank — shown on the participant dashboard. Participants upload ONE answer file
(the existing Submission). The judge, grading that submission, sees the team's
paper to score per question; or the AI auto-checks against each question's answer.
"""

import uuid

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id = Column(UUID(as_uuid=True), ForeignKey("rounds.id"), nullable=False, index=True)

    text = Column(String, nullable=False)
    # MCQ options (list[str]); empty/None ⇒ an open-ended / written question.
    options = Column(JSONB, nullable=True)
    # The correct answer (option text for MCQ, or a model answer/keyword for open).
    # Nullable: when absent the question must be graded by a human, not auto-checked.
    correct_answer = Column(String, nullable=True)
    marks = Column(Float, default=1.0, server_default="1", nullable=False)
    position = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class QuestionPaper(Base):
    __tablename__ = "question_papers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id = Column(UUID(as_uuid=True), ForeignKey("rounds.id"), nullable=False, index=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False, index=True)

    # The ordered list of Question ids that make up this team's paper (JSONB so no
    # join table is needed; the bank lives in `questions`).
    question_ids = Column(JSONB, nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
