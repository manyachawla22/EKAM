from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.middleware.auth import require_role
from app.models.user import User, UserRole
from app.models.report import Report
from app.schemas.report import Report as ReportSchema, ReportCreate

router = APIRouter()

@router.post("/generate", response_model=ReportSchema, status_code=status.HTTP_201_CREATED)
async def generate_report(
    report_in: ReportCreate,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    # In a real app, this would trigger background tasks to aggregate data
    new_report = Report(**report_in.model_dump())
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    return new_report

@router.get("/{event_id}", response_model=List[ReportSchema])
async def list_reports(
    event_id: UUID,
    current_user: User = Depends(require_role([UserRole.organizer])),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Report).where(Report.event_id == event_id))
    return result.scalars().all()
