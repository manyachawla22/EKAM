from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_role

from app.models.user import User, UserRole

from app.schemas.report import (
    Report,
    ReportCreate
)

from app.services.report_service import (
    create_report_service,
    list_reports_service
)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)


@router.post(
    "/generate",
    response_model=Report,
    status_code=status.HTTP_201_CREATED
)
async def generate_report(
    report_in: ReportCreate,
    current_user: User = Depends(
        require_role([
            UserRole.organizer,
            UserRole.admin
        ])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await create_report_service(
        db,
        report_in
    )


@router.get(
    "/{event_id}",
    response_model=List[Report]
)
async def list_reports(
    event_id: UUID,
    current_user: User = Depends(
        require_role([
            UserRole.organizer,
            UserRole.admin
        ])
    ),
    db: AsyncSession = Depends(get_db)
):
    return await list_reports_service(
        db,
        event_id
    )