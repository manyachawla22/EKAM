from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.middleware.auth import require_role
from app.models.user import User, UserRole
from app.models.judge import JudgeAssignment
from app.schemas.judge import JudgeAssignment as JudgeAssignmentSchema, JudgeAssignmentCreate

router = APIRouter()

@router.post("/assign", response_model=JudgeAssignmentSchema, status_code=status.HTTP_201_CREATED)
async def assign_judge(
    assign_in: JudgeAssignmentCreate,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    new_assign = JudgeAssignment(**assign_in.model_dump())
    db.add(new_assign)
    await db.commit()
    await db.refresh(new_assign)
    return new_assign

@router.get("/{event_id}", response_model=List[JudgeAssignmentSchema])
async def list_judges_for_event(
    event_id: UUID,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(JudgeAssignment).where(JudgeAssignment.event_id == event_id))
    return result.scalars().all()
