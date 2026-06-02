"""
EKAM Rubrics Router

Per-round scoring criteria. Judges read them to score; organizers manage them.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import AuthContext
from app.core.database import get_db
from app.middleware.auth import require_actor_type
from app.schemas.rubric import (
    RubricCriterionResponse,
    RubricCriterionCreate,
    RubricCriterionUpdate,
)
from app.services import rubric_service

router = APIRouter(
    prefix="/rubrics",
    tags=["Rubrics"],
)


@router.get(
    "/round/{round_id}",
    response_model=List[RubricCriterionResponse],
    dependencies=[Depends(require_actor_type(["organizer", "judge", "participant"]))],
)
async def list_round_rubric(
    round_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List a round's rubric criteria (seeds defaults the first time)."""
    return await rubric_service.list_criteria(db, round_id)


@router.post(
    "/round/{round_id}",
    response_model=RubricCriterionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["organizer"]))],
)
async def add_criterion(
    round_id: UUID,
    body: RubricCriterionCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    return await rubric_service.create_criterion(db, round_id, body)


@router.post(
    "/round/{round_id}/generate",
    response_model=List[RubricCriterionResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["organizer"]))],
)
async def generate_rubric(
    round_id: UUID,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    """(Re)generate this round's rubric from the event context via AI."""
    return await rubric_service.generate_criteria_with_ai(db, round_id)


@router.put(
    "/criterion/{criterion_id}",
    response_model=RubricCriterionResponse,
    dependencies=[Depends(require_actor_type(["organizer"]))],
)
async def edit_criterion(
    criterion_id: UUID,
    body: RubricCriterionUpdate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    return await rubric_service.update_criterion(db, criterion_id, body)


@router.delete(
    "/criterion/{criterion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_actor_type(["organizer"]))],
)
async def remove_criterion(
    criterion_id: UUID,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    await rubric_service.delete_criterion(db, criterion_id)
    return None
