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


# -------------------- TEAM MEMBER --------------------

class TeamMemberCreate(BaseModel):
    team_id: UUID
    participant_id: UUID
    is_leader: bool = False


# A compact participant view used inside TeamMemberResponse so the frontend
# can render member names without an extra round-trip per row.
class _ParticipantInMember(BaseModel):
    id: UUID
    name: str
    email: str
    institution: Optional[str] = None
    skills: List[str] = []

    class Config:
        from_attributes = True


class TeamMemberResponse(BaseModel):
    id: UUID

    team_id: UUID
    participant_id: UUID

    is_leader: bool

    joined_at: datetime

    participant: Optional[_ParticipantInMember] = None

    class Config:
        from_attributes = True


class TeamResponse(TeamBase):
    id: UUID

    event_id: UUID
    theme_id: Optional[UUID]

    created_at: datetime

    # Eager-loaded by the team service. Empty list when there are no members
    # yet (not None) so the frontend can always do `team.members.length`.
    members: List[TeamMemberResponse] = []

    class Config:
        from_attributes = True


Team = TeamResponse
TeamMember = TeamMemberResponse


# -------------------- TEAM PREFERENCE --------------------

class TeamPreferenceCreate(BaseModel):
    preferred_name: str
    preferred_theme_id: Optional[UUID] = None


class TeamPreferenceResponse(BaseModel):
    id: UUID
    team_id: UUID
    participant_id: UUID
    preferred_name: str
    preferred_theme_id: Optional[UUID] = None
    submitted_at: datetime

    class Config:
        from_attributes = True


TeamPreference = TeamPreferenceResponse


# -------------------- TEAM THEME UPDATE --------------------

class TeamThemeUpdate(BaseModel):
    theme_id: Optional[UUID] = None
