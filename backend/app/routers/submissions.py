from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import get_current_user

from app.models.user import User

from app.schemas.submission import (
    Submission,
    SubmissionCreate
)

from app.services.submission_service import (
    create_submission_service,
    list_submissions_service
)

router = APIRouter(
    prefix="/submissions",
    tags=["Submissions"]
)


@router.post(
    "/upload",
    response_model=Submission,
    status_code=status.HTTP_201_CREATED
)
async def upload_submission(
    submission_in: SubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await create_submission_service(
        db,
        submission_in
    )


@router.get(
    "/{round_id}",
    response_model=List[Submission]
)
async def list_submissions(
    round_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await list_submissions_service(
        db,
        round_id
    )