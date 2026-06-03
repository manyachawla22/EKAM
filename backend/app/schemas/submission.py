from pydantic import BaseModel
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime

from app.models.submission import SubmissionStatus


# -------------------- SUBMISSION --------------------

class SubmissionBase(BaseModel):
    attachments: List[str] = []


class SubmissionCreate(SubmissionBase):
    team_id: UUID
    round_id: UUID


class TeamMini(BaseModel):
    """Just enough of the team to render its name instead of a raw id."""
    id: UUID
    name: str

    class Config:
        from_attributes = True


class SubmissionResponse(SubmissionBase):
    id: UUID

    team_id: UUID
    round_id: UUID

    # Resolved team so the UI shows the team name, not the raw id.
    team: Optional[TeamMini] = None

    status: SubmissionStatus

    final_score: Optional[float]
    panel_average: Optional[float]

    submitted_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# -------------------- EVALUATION --------------------

class EvaluationBase(BaseModel):
    rubric_scores: Dict[str, float]
    feedback: Optional[str] = None


class EvaluationCreate(EvaluationBase):
    submission_id: UUID
    judge_id: UUID
    total_score: float


class EvaluationResponse(EvaluationBase):
    id: UUID

    submission_id: UUID
    judge_id: UUID

    total_score: float

    evaluated_at: datetime

    class Config:
        from_attributes = True

Submission = SubmissionResponse
Evaluation = EvaluationResponse