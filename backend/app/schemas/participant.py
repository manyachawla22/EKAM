from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.participant import RegistrationStatus

class ParticipantBase(BaseModel):
    institution: Optional[str] = None
    skills: List[str] = []
    gender: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None

class ParticipantCreate(ParticipantBase):
    user_id: UUID
    event_id: UUID

class Participant(ParticipantBase):
    id: UUID
    user_id: UUID
    event_id: UUID
    ats_score: Optional[float] = None
    status: RegistrationStatus
    created_at: datetime

    class Config:
        from_attributes = True

class TeamBase(BaseModel):
    name: str

class TeamCreate(TeamBase):
    event_id: UUID

class Team(TeamBase):
    id: UUID
    event_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class TeamMemberBase(BaseModel):
    is_leader: int = 0

class TeamMemberCreate(TeamMemberBase):
    team_id: UUID
    participant_id: UUID

class TeamMember(TeamMemberBase):
    id: UUID
    team_id: UUID
    participant_id: UUID
    joined_at: datetime

    class Config:
        from_attributes = True
