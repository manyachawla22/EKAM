"""
EKAM Evaluations Router
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_actor_type
from app.core.auth_context import AuthContext

from app.schemas.evaluation import (
    Evaluation,
    EvaluationCreate
)

from app.services.evaluation_service import (
    submit_evaluation_service,
    get_submission_evaluations_service
)

router = APIRouter(
    prefix="/evaluations",
    tags=["Evaluations"]
)


@router.post(
    "/submit",
    response_model=Evaluation,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["judge"]))]
)
async def submit_evaluation(
    evaluation_in: EvaluationCreate,
    auth: AuthContext = Depends(require_actor_type(["judge"])),
    db: AsyncSession = Depends(get_db)
):
    # Depending on schema, evaluate if the judge belongs to the right event
    return await submit_evaluation_service(
        db,
        evaluation_in
    )


@router.get(
    "/{submission_id}",
    response_model=List[Evaluation],
    dependencies=[Depends(require_actor_type(["organizer", "judge"]))]
)
async def get_submission_evaluations(
    submission_id: UUID,
    auth: AuthContext = Depends(require_actor_type(["organizer", "judge"])),
    db: AsyncSession = Depends(get_db)
):
    return await get_submission_evaluations_service(
        db,
        submission_id
    )