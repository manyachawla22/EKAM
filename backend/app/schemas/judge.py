from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# -------------------- JUDGE --------------------

class JudgeBase(BaseModel):
    name: str
    email: EmailStr

    institution: Optional[str] = None

    expertise: List[str] = []


class JudgeCreate(JudgeBase):
    event_id: UUID


class JudgeUpdate(BaseModel):
    institution: Optional[str] = None
    expertise: Optional[List[str]] = None


class JudgeResponse(JudgeBase):
    id: UUID

    event_id: UUID

    rating: float

    is_verified: bool

    last_login: Optional[datetime]

    created_at: datetime

    class Config:
        from_attributes = True


# -------------------- JUDGE ASSIGNMENT --------------------

class JudgeAssignmentCreate(BaseModel):
    judge_id: UUID
    team_id: UUID
    round_id: UUID


class JudgeAssignmentResponse(BaseModel):
    id: UUID

    judge_id: UUID
    team_id: UUID
    round_id: UUID

    assigned_at: datetime

    class Config:
        from_attributes = True

Judge = JudgeResponse
JudgeAssignment = JudgeAssignmentResponse