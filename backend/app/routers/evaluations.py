from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.middleware.auth import require_role
from app.models.user import User, UserRole
from app.models.submission import Evaluation, Submission, SubmissionStatus
from app.schemas.submission import Evaluation as EvaluationSchema, EvaluationCreate

router = APIRouter()

@router.post("/submit", response_model=EvaluationSchema, status_code=status.HTTP_201_CREATED)
async def submit_evaluation(
    eval_in: EvaluationCreate,
    current_user: User = Depends(require_role([UserRole.judge])),
    db: AsyncSession = Depends(get_db)
):
    new_eval = Evaluation(**eval_in.model_dump())
    db.add(new_eval)
    
    # Update submission status to reviewed
    sub_res = await db.execute(select(Submission).where(Submission.id == eval_in.submission_id))
    submission = sub_res.scalars().first()
    if submission:
        submission.status = SubmissionStatus.reviewed
        # Simple score update for MVP
        submission.score = eval_in.score
        
    await db.commit()
    await db.refresh(new_eval)
    return new_eval

@router.get("/{submission_id}", response_model=List[EvaluationSchema])
async def list_evaluations(
    submission_id: UUID,
    current_user: User = Depends(require_role([UserRole.organizer, UserRole.judge])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Evaluation).where(Evaluation.submission_id == submission_id))
    return result.scalars().all()
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_role

from app.models.user import User, UserRole

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
    status_code=status.HTTP_201_CREATED
)
async def submit_evaluation(
    evaluation_in: EvaluationCreate,
    current_user: User = Depends(
        require_role([UserRole.judge])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await submit_evaluation_service(
        db,
        evaluation_in
    )


@router.get(
    "/{submission_id}",
    response_model=List[Evaluation]
)
async def get_submission_evaluations(
    submission_id: UUID,
    current_user: User = Depends(
        require_role([
            UserRole.organizer,
            UserRole.admin,
            UserRole.judge
        ])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await get_submission_evaluations_service(
        db,
        submission_id
    )