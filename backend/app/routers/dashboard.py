"""
EKAM Dashboard Router
"""

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.middleware.auth import require_actor_type, require_event_access
from app.core.auth_context import AuthContext

from app.services.dashboard_service import (
    organizer_dashboard_service,
    participant_dashboard_service,
    judge_dashboard_service
)

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get(
    "/organizer/{event_id}",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def organizer_dashboard(
    event_id: str,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Get aggregated metrics for the organizer."""
    return await organizer_dashboard_service(
        db,
        event_id
    )


@router.get(
    "/participant/{event_id}",
    dependencies=[
        Depends(require_actor_type(["participant"])),
        Depends(require_event_access("event_id"))
    ]
)
async def participant_dashboard(
    event_id: str,
    auth: AuthContext = Depends(require_actor_type(["participant"])),
    db: AsyncSession = Depends(get_db)
):
    """Get specific details for a participant (team, submissions)."""
    return await participant_dashboard_service(
        db,
        event_id,
        auth.actor_id
    )


@router.get(
    "/judge/{event_id}",
    dependencies=[
        Depends(require_actor_type(["judge"])),
        Depends(require_event_access("event_id"))
    ]
)
async def judge_dashboard(
    event_id: str,
    auth: AuthContext = Depends(require_actor_type(["judge"])),
    db: AsyncSession = Depends(get_db)
):
    """Get specific details for a judge (assignments, evaluations)."""
    return await judge_dashboard_service(
        db,
        event_id,
        auth.actor_id
    )