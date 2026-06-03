"""
EKAM Reports Router
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_context import AuthContext
from app.core.database import get_db
from app.middleware.auth import require_actor_type, require_event_access
from app.schemas.report import Report as ReportSchema, ReportCreate
from app.services.ml_anomaly_report_service import analyze_evaluation
from app.services.participant_performance_report_service import (
    generate_participant_performance_report_service,
)
from app.services.plagiarism_service import detect_plagiarism_service
from app.services.report_service import (
    create_report_service,
    list_reports_service,
    generate_event_summary_report_service,
)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


@router.post(
    "/generate",
    response_model=ReportSchema,
    status_code=status.HTTP_201_CREATED,
)
async def generate_report(
    report_in: ReportCreate,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    if not auth.can_access_event(str(report_in.event_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No event access",
        )

    return await create_report_service(db, report_in)


@router.post(
    "/{event_id}/generate",
    response_model=ReportSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id")),
    ],
)
async def generate_event_summary_report(
    event_id: UUID,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db),
):
    """Build (and email) the rich event-summary report with standings + charts."""
    return await generate_event_summary_report_service(
        db=db,
        event_id=event_id,
        requested_by=auth.actor_id,
    )


@router.post(
    "/detect-anomalies/{event_id}",
    response_model=ReportSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id")),
    ],
)
async def detect_anomaly_scores(
    event_id: UUID,
    contamination: float = 0.1,
    db: AsyncSession = Depends(get_db),
):
    return await analyze_evaluation(
        db=db,
        event_id=event_id,
        contamination=contamination,
    )


@router.post(
    "/detect-plagiarism/{event_id}",
    response_model=ReportSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id")),
    ],
)
async def detect_plagiarism(
    event_id: UUID,
    threshold: float = 0.8,
    db: AsyncSession = Depends(get_db),
):
    return await detect_plagiarism_service(
        db=db,
        event_id=str(event_id),
        threshold=threshold,
    )


@router.get(
    "/participant/{event_id}/{participant_id}",
    dependencies=[
        Depends(require_event_access("event_id")),
    ],
)
async def generate_participant_performance_report(
    event_id: UUID,
    participant_id: UUID,
    auth: AuthContext = Depends(require_actor_type(["organizer", "participant"])),
    db: AsyncSession = Depends(get_db),
):
    return await generate_participant_performance_report_service(
        db=db,
        event_id=event_id,
        participant_id=participant_id,
        auth=auth,
    )


@router.get(
    "/{event_id}",
    response_model=List[ReportSchema],
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id")),
    ],
)
async def list_reports(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await list_reports_service(db, event_id)