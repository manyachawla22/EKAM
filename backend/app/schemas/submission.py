from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.submission import SubmissionStatus

class SubmissionBase(BaseModel):
    attachments: List[str] = []

class SubmissionCreate(SubmissionBase):
    team_id: UUID
    round_id: UUID

class Submission(SubmissionBase):
    id: UUID
    team_id: UUID
    round_id: UUID
    status: SubmissionStatus
    score: Optional[float] = None
    panel_avg: Optional[float] = None
    feedback: Optional[str] = None
    submitted_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class EvaluationBase(BaseModel):
    score: float
    feedback: Optional[str] = None

class EvaluationCreate(EvaluationBase):
    submission_id: UUID
    judge_id: UUID

class Evaluation(EvaluationBase):
    id: UUID
    submission_id: UUID
    judge_id: UUID
    evaluated_at: datetime

    class Config:
        from_attributes = True
