from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# -------------------- TEAM --------------------

class TeamBase(BaseModel):
    name: str


class TeamCreate(TeamBase):
    event_id: UUID
    theme_id: Optional[UUID] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    theme_id: Optional[UUID] = None


class TeamResponse(TeamBase):
    id: UUID

    event_id: UUID
    theme_id: Optional[UUID]

    created_at: datetime

    class Config:
        from_attributes = True


# -------------------- TEAM MEMBER --------------------

class TeamMemberCreate(BaseModel):
    team_id: UUID
    participant_id: UUID
    is_leader: bool = False


class TeamMemberResponse(BaseModel):
    id: UUID

    team_id: UUID
    participant_id: UUID

    is_leader: bool

    joined_at: datetime

    class Config:
        from_attributes = True