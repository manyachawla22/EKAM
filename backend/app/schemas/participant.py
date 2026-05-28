from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.models.participant import RegistrationStatus


class ParticipantBase(BaseModel):
    name: str
    email: EmailStr

    institution: Optional[str] = None
    phone: Optional[str] = None

    gender: Optional[str] = None
    age: Optional[int] = None

    skills: List[str] = []


class ParticipantCreate(ParticipantBase):
    event_id: UUID


class ParticipantUpdate(BaseModel):
    institution: Optional[str] = None
    phone: Optional[str] = None
    skills: Optional[List[str]] = None


class ParticipantResponse(ParticipantBase):
    id: UUID

    event_id: UUID

    ats_score: Optional[float]

    status: RegistrationStatus

    is_verified: bool

    last_login: Optional[datetime]

    created_at: datetime

    class Config:
        from_attributes = True