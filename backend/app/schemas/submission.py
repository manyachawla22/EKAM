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


class SubmissionResponse(SubmissionBase):
    id: UUID

    team_id: UUID
    round_id: UUID

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