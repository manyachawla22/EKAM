from pydantic import BaseModel
from typing import Any, Dict
from uuid import UUID
from datetime import datetime

class ReportBase(BaseModel):
    title: str
    type: str
    data: Dict[str, Any] = {}

class ReportCreate(ReportBase):
    event_id: UUID

class ReportResponse(ReportBase):
    id: UUID
    event_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

Report = ReportResponse
