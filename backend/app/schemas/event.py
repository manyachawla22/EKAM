from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.models.event import (
    EventStatus,
    EventStage,
    RoundStatus,
    TeamFormationType
)


# -------------------- ROUND --------------------

class RoundBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoundCreate(RoundBase):
    event_id: UUID


class RoundResponse(RoundBase):
    id: UUID
    event_id: UUID
    status: RoundStatus
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------- EVENT --------------------

class EventBase(BaseModel):
    name: str
    type: str
    description: Optional[str] = None

    max_participants: int = 0

    min_team_size: int = 1
    max_team_size: int = 4

    team_formation_type: TeamFormationType


class EventCreate(EventBase):
    hash: str
    organizer_id: UUID


class EventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

    stage: Optional[EventStage] = None
    status: Optional[EventStatus] = None

    max_participants: Optional[int] = None

    min_team_size: Optional[int] = None
    max_team_size: Optional[int] = None


class EventResponse(EventBase):
    id: UUID
    organizer_id: UUID

    status: EventStatus
    stage: EventStage

    created_at: datetime
    updated_at: Optional[datetime]

    rounds: List[RoundResponse] = []

    class Config:
        from_attributes = True

Event = EventResponse