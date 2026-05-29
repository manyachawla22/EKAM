from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_actor, require_actor_type
from app.core.auth_context import AuthContext

from app.schemas.submission import (
    Submission,
    SubmissionCreate,
)

from app.services.submission_service import (
    create_submission_service,
    list_submissions_service,
)

router = APIRouter(
    prefix="/submissions",
    tags=["Submissions"],
)


@router.post(
    "/upload",
    response_model=Submission,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["participant"]))],
)
async def upload_submission(
    submission_in: SubmissionCreate,
    auth: AuthContext = Depends(require_actor_type(["participant"])),
    db: AsyncSession = Depends(get_db),
):
    """Participants upload a submission for their team."""
    return await create_submission_service(db, submission_in)


@router.get(
    "/{round_id}",
    response_model=List[Submission],
    dependencies=[Depends(require_actor_type(["organizer", "judge", "participant"]))],
)
async def list_submissions(
    round_id: UUID,
    auth: AuthContext = Depends(get_current_actor),
    db: AsyncSession = Depends(get_db),
):
    """List all submissions for a round."""
    return await list_submissions_service(db, round_id)
