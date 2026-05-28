from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ThemeBase(BaseModel):
    name: str
    description: Optional[str] = None
    required_skills: List[str] = []


class ThemeCreate(ThemeBase):
    event_id: UUID


class ThemeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None


class ThemeResponse(ThemeBase):
    id: UUID
    event_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True