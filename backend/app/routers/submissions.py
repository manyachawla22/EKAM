from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.middleware.auth import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.submission import Submission
from app.schemas.submission import Submission as SubmissionSchema, SubmissionCreate

router = APIRouter()

@router.post("/upload", response_model=SubmissionSchema, status_code=status.HTTP_201_CREATED)
async def upload_submission(
    sub_in: SubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Depending on complex team role checks, a participant should only upload for their team
    new_sub = Submission(**sub_in.model_dump())
    db.add(new_sub)
    await db.commit()
    await db.refresh(new_sub)
    return new_sub

@router.get("/{event_id}", response_model=List[SubmissionSchema])
async def list_submissions(
    event_id: UUID,
    current_user: User = Depends(require_role([UserRole.organizer, UserRole.judge])),
    db: AsyncSession = Depends(get_db)
):
    # For now, it returns all submissions for an event by joining rounds. 
    # Proper implementation would join Round where round.event_id == event_id
    from app.models.event import Round
    result = await db.execute(
        select(Submission).join(Round, Submission.round_id == Round.id).where(Round.event_id == event_id)
    )
    return result.scalars().all()
