from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class JudgeBase(BaseModel):
    expertise: List[str] = []
    institution: Optional[str] = None
    rating: float = 5.0

class JudgeCreate(JudgeBase):
    user_id: UUID

class Judge(JudgeBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class JudgeAssignmentBase(BaseModel):
    pass

class JudgeAssignmentCreate(JudgeAssignmentBase):
    judge_id: UUID
    event_id: UUID
    round_id: Optional[UUID] = None

class JudgeAssignment(JudgeAssignmentBase):
    id: UUID
    judge_id: UUID
    event_id: UUID
    round_id: Optional[UUID]
    assigned_at: datetime

    class Config:
        from_attributes = True
