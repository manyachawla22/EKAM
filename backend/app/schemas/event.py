from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.models.event import EventStatus, EventStage, RoundStatus

class RoundBase(BaseModel):
    name: str
    status: RoundStatus = RoundStatus.upcoming
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class RoundCreate(RoundBase):
    event_id: UUID

class Round(RoundBase):
    id: UUID
    event_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class EventBase(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    status: EventStatus = EventStatus.draft
    stage: EventStage = EventStage.draft
    max_participants: int = 0

class EventCreate(EventBase):
    hash: str
    organizer_id: UUID

class EventUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[EventStatus] = None
    stage: Optional[EventStage] = None
    max_participants: Optional[int] = None

class Event(EventBase):
    id: UUID
    hash: str
    organizer_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    rounds: List[Round] = []

    class Config:
        from_attributes = True
