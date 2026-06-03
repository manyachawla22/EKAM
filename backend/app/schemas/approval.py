from uuid import UUID
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.models.approval import RequestType, ApprovalStatus


class ApprovalRequestBase(BaseModel):
    event_id: UUID
    request_type: RequestType
    payload: Dict[str, Any] = Field(..., description="The proposed data to be approved")


class ApprovalRequestCreate(ApprovalRequestBase):
    pass


class ApprovalRequestResponse(ApprovalRequestBase):
    id: UUID
    status: ApprovalStatus
    requested_by: Optional[UUID] = None
    reviewed_by: Optional[UUID] = None
    review_notes: Optional[str] = None
    requested_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovalAction(BaseModel):
    action: ApprovalStatus = Field(..., description="approve, reject, or revise")
    review_notes: Optional[str] = None
    # For pipeline advancement approvals: the qualifying score the organizer
    # picks from the leaderboard. Teams scoring >= this advance; the rest are
    # eliminated. Ignored for other request types.
    cutoff_score: Optional[float] = None
