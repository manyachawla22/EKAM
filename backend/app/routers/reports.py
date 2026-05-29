"""
EKAM Reports Router
"""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_actor_type, require_event_access
from app.core.auth_context import AuthContext

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
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_actor_type(["organizer"]))]
)
async def generate_report(
    report_in: ReportCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    if not auth.can_access_event(str(report_in.event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access"
        )
        
    return await create_report_service(
        db,
        report_in
    )


@router.get(
    "/{event_id}",
    response_model=List[Report],
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def list_reports(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    return await list_reports_service(
        db,
        event_id
    )