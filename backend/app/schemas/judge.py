from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class InviteStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"


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


# -------------------- JUDGE ASSIGNMENT DETAIL (for judge dashboard) ----------

class JudgeAssignmentDetail(BaseModel):
    assignment_id: UUID
    round_id: UUID
    round_name: str
    round_status: str
    team_id: UUID
    team_name: str
    submission_id: Optional[UUID] = None
    submission_status: Optional[str] = None
    already_evaluated: bool = False

    class Config:
        from_attributes = True


# -------------------- JUDGE INVITE --------------------

class JudgeInviteDetail(BaseModel):
    judge_name: str
    judge_email: str
    event_name: str
    event_hash: str
    invite_status: str


class JudgeInviteRespond(BaseModel):
    token: UUID
    accepted: bool