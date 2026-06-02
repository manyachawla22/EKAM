from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class RubricCriterionBase(BaseModel):
    name: str
    description: Optional[str] = None
    max_score: float = 10.0
    position: int = 0


class RubricCriterionCreate(RubricCriterionBase):
    pass


class RubricCriterionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_score: Optional[float] = None
    position: Optional[int] = None


class RubricCriterionResponse(RubricCriterionBase):
    id: UUID
    round_id: UUID

    class Config:
        from_attributes = True
