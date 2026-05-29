"""
EKAM Anomalies Router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.auth_context import AuthContext
from app.middleware.auth import require_actor_type, require_event_access

from app.models.anomaly import Anomaly

router = APIRouter(
    prefix="/anomalies",
    tags=["Anomalies"]
)

@router.get(
    "/{event_id}",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def list_anomalies(
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all anomalies detected for an event."""
    result = await db.execute(
        select(Anomaly).where(Anomaly.event_id == event_id).order_by(Anomaly.created_at.desc())
    )
    return result.scalars().all()


@router.post(
    "/{event_id}/{anomaly_id}/resolve",
    dependencies=[
        Depends(require_actor_type(["organizer"])),
        Depends(require_event_access("event_id"))
    ]
)
async def resolve_anomaly(
    event_id: str,
    anomaly_id: str,
    auth: AuthContext = Depends(require_actor_type(["organizer"])),
    db: AsyncSession = Depends(get_db)
):
    """Mark an anomaly as resolved."""
    from datetime import datetime, timezone
    
    result = await db.execute(
        select(Anomaly).where(Anomaly.id == anomaly_id, Anomaly.event_id == event_id)
    )
    anomaly = result.scalars().first()
    
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
        
    anomaly.is_resolved = True
    anomaly.resolved_by = auth.actor_id
    anomaly.resolved_at = datetime.now(timezone.utc)
    
    await db.commit()
    return {"message": "Anomaly resolved"}
